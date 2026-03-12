from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date

from rest_framework import permissions, status, viewsets
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from bookings.models import Booking
from .models import Ground, GroundAvailability
from .serializers import (
    AvailabilityBulkUpsertSerializer,
    GroundCreateSerializer,
    GroundDetailSerializer,
    GroundListSerializer,
    OwnerGroundEditSerializer,
)
from .slot_constants import FIXED_SLOTS


class GroundViewSet(viewsets.ModelViewSet):
    queryset = Ground.objects.all().order_by("-created_at")
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.action == "create":
            return GroundCreateSerializer
        if self.action == "list":
            return GroundListSerializer
        return GroundDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        if self.action in ["list", "retrieve"]:
            qs = qs.filter(status=Ground.Status.APPROVED)

        params = self.request.query_params
        search = (params.get("search") or "").strip()
        max_price = (params.get("max_price") or "").strip()
        date_str = (params.get("date") or "").strip()

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(location__icontains=search))

        if max_price:
            try:
                qs = qs.filter(price_per_hour__lte=int(max_price))
            except ValueError:
                pass

        if date_str:
            d = parse_date(date_str)
            if d:
                dow = d.weekday()
                keep_ids = []

                for g in qs:
                    windows = list(
                        GroundAvailability.objects.filter(ground=g, day_of_week=dow)
                    )

                    def slot_open(start_str, end_str):
                        if not windows:
                            return True
                        for w in windows:
                            w_start = w.start_time.strftime("%H:%M")
                            w_end = w.end_time.strftime("%H:%M")
                            if w_start <= start_str and end_str <= w_end:
                                return True
                        return False

                    bookings = Booking.objects.filter(
                        ground=g,
                        date=d,
                        status=Booking.Status.BOOKED,
                    )

                    found_available = False
                    for s, e in FIXED_SLOTS:
                        start_str = s.strftime("%H:%M")
                        end_str = e.strftime("%H:%M")

                        is_booked = False
                        for b in bookings:
                            if s >= b.start_time and s < b.end_time:
                                is_booked = True
                                break

                        if slot_open(start_str, end_str) and not is_booked:
                            found_available = True
                            break

                    if found_available:
                        keep_ids.append(g.id)

                qs = qs.filter(id__in=keep_ids)

        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user, status=Ground.Status.PENDING)


class OwnerMyGroundsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Ground.objects.filter(owner=request.user).order_by("-created_at")
        serializer = OwnerGroundEditSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class OwnerGroundDetailUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_object(self, request, pk):
        return get_object_or_404(Ground, pk=pk, owner=request.user)

    def get(self, request, pk):
        ground = self.get_object(request, pk)
        serializer = OwnerGroundEditSerializer(ground, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        print("PATCH DATA:", request.data)
        print("PATCH FILES:", request.FILES)

        ground = self.get_object(request, pk)
        serializer = OwnerGroundEditSerializer(
            ground,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        print("PUT DATA:", request.data)
        print("PUT FILES:", request.FILES)

        ground = self.get_object(request, pk)
        serializer = OwnerGroundEditSerializer(
            ground,
            data=request.data,
            partial=False,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class GroundAvailabilityBulkUpsertView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        ground = get_object_or_404(Ground, pk=pk)

        if ground.owner_id != request.user.pk:
            return Response(
                {"detail": "Not allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AvailabilityBulkUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data["availability"]

        with transaction.atomic():
            days = [d["day_of_week"] for d in data]

            GroundAvailability.objects.filter(
                ground=ground,
                day_of_week__in=days
            ).delete()

            to_create = []
            for d in data:
                dow = d["day_of_week"]
                for w in d["windows"]:
                    to_create.append(
                        GroundAvailability(
                            ground=ground,
                            day_of_week=dow,
                            start_time=w["start_time"],
                            end_time=w["end_time"],
                        )
                    )

            GroundAvailability.objects.bulk_create(to_create)

        return Response(
            {"detail": "Availability saved successfully."},
            status=status.HTTP_200_OK
        )


class GroundSlotsForDateView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        ground = get_object_or_404(Ground, pk=pk, status=Ground.Status.APPROVED)

        date_str = request.query_params.get("date")
        d = parse_date(date_str) if date_str else None

        if not d:
            return Response(
                {"detail": "date=YYYY-MM-DD is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        dow = d.weekday()

        windows = list(
            GroundAvailability.objects.filter(ground=ground, day_of_week=dow)
        )

        def within_availability(start_str, end_str):
            if not windows:
                return True
            for w in windows:
                w_start = w.start_time.strftime("%H:%M")
                w_end = w.end_time.strftime("%H:%M")
                if w_start <= start_str and end_str <= w_end:
                    return True
            return False

        bookings = Booking.objects.filter(
            ground=ground,
            date=d,
            status=Booking.Status.BOOKED,
        )

        slots = []
        for s, e in FIXED_SLOTS:
            start_str = s.strftime("%H:%M")
            end_str = e.strftime("%H:%M")

            open_ = within_availability(start_str, end_str)

            is_booked = False
            for b in bookings:
                if s >= b.start_time and s < b.end_time:
                    is_booked = True
                    break

            slots.append({
                "start_time": start_str,
                "end_time": end_str,
                "booked": bool(is_booked),
                "available": bool(open_ and not is_booked),
            })

        return Response(
            {
                "ground_id": ground.id,
                "date": date_str,
                "slots": slots,
            },
            status=status.HTTP_200_OK
        )