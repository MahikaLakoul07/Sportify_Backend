# users/views.py

# Generic views help us build common API behaviors like create, retrieve, list, update, etc.
from rest_framework import generics, status

# Import Response so we can return custom JSON responses from our API views.
from rest_framework.response import Response

# Import permission classes.
# AllowAny means anyone can access that API endpoint even without logging in.
# IsAuthenticated means only logged-in users with a valid token can access it.
from rest_framework.permissions import AllowAny, IsAuthenticated

# Import RefreshToken from SimpleJWT.
# This is used to generate JWT refresh and access tokens after registration or login.
from rest_framework_simplejwt.tokens import RefreshToken

# Import get_user_model so Django gives us the currently active User model.
# This is useful because your project uses a custom User model.
from django.contrib.auth import get_user_model

# Import serializers used in this views file.
# RegisterSerializer handles signup validation and user creation.
# LoginSerializer handles login validation.
# ProfileSerializer handles returning safe profile information.
from .serializers import RegisterSerializer, LoginSerializer, ProfileSerializer

# Get the currently active custom User model.
User = get_user_model()


# REGISTER VIEW
# This API view is responsible for registering a new user.
# It uses CreateAPIView because registration creates a new record in the database.
class RegisterView(generics.CreateAPIView):

    # Tell this view to use RegisterSerializer for validating request data
    # and creating a new user.
    serializer_class = RegisterSerializer

    # Allow anyone to access this endpoint.
    # A user does not need to be logged in to register.
    permission_classes = [AllowAny]

    # Override the default create() method so we can:
    # 1. validate incoming data
    # 2. create the user
    # 3. generate JWT tokens immediately
    # 4. return custom JSON response
    def create(self, request, *args, **kwargs):

        # Create serializer instance using incoming request data.
        serializer = self.get_serializer(data=request.data)

        # Validate the request data.
        # If validation fails, an error response is automatically returned.
        serializer.is_valid(raise_exception=True)

        # Save the new user into the database.
        # This calls the create() method inside RegisterSerializer.
        user = serializer.save()

        # Generate JWT refresh token for the newly registered user.
        refresh = RefreshToken.for_user(user)

        # Generate access token from refresh token.
        # Access token is used for authenticated requests.
        access_token = str(refresh.access_token)

        # Return custom response with user details and tokens.
        return Response(
            {
                "user": {
                    # Return the unique ID of the created user.
                    "user_id": user.user_id,

                    # Return username of the created user.
                    "username": user.username,

                    # Return email of the created user.
                    "email": user.email,

                    # Return phone number of the created user.
                    "phone": user.phone,

                    # Return whether the user is a player or owner.
                    "user_type": user.user_type,

                    # Return user's gender.
                    "gender": user.gender,
                },

                # Return refresh token as string.
                "refresh": str(refresh),

                # Return access token as string.
                "access": access_token,
            },

            # Return HTTP 201 status code meaning "Created successfully".
            status=status.HTTP_201_CREATED,
        )


# LOGIN VIEW
# This API view is responsible for logging in an existing user.
# GenericAPIView is used because login does not directly map to create/list/update/retrieve model behavior.
class LoginView(generics.GenericAPIView):

    # Use LoginSerializer to validate email and password.
    serializer_class = LoginSerializer

    # Allow anyone to access login endpoint.
    # A person obviously needs to be able to log in before being authenticated.
    permission_classes = [AllowAny]

    # Handle POST request for login.
    def post(self, request):

        # Pass incoming login data into serializer.
        serializer = self.get_serializer(data=request.data)

        # Validate login credentials.
        # If email/password is invalid, serializer raises validation error automatically.
        serializer.is_valid(raise_exception=True)

        # Get the authenticated user object from validated serializer data.
        # This was attached inside LoginSerializer.validate().
        user = serializer.validated_data["user"]

        # Create refresh token for the logged-in user.
        refresh = RefreshToken.for_user(user)

        # Create access token from the refresh token.
        access_token = str(refresh.access_token)

        # Prepare custom response data.
        response = Response({
            "user": {
                # Return user ID.
                "user_id": user.user_id,

                # Return username.
                "username": user.username,

                # Return email.
                "email": user.email,

                # Return phone number.
                "phone": user.phone,

                # Return user type.
                "user_type": user.user_type,
            },

            # Return refresh token.
            "refresh": str(refresh),

            # Return access token.
            "access": access_token,
        }, status=status.HTTP_200_OK)

        # Store access token inside an HttpOnly cookie.
        # httponly=True means JavaScript in the browser cannot directly read this cookie.
        # This improves protection against some XSS attacks.
        # max_age=3600 means the cookie lasts for 1 hour (3600 seconds).
        response.set_cookie("access", access_token, httponly=True, max_age=3600)

        # Store refresh token inside an HttpOnly cookie.
        # max_age=7*24*3600 means the cookie lasts 7 days.
        response.set_cookie("refresh", str(refresh), httponly=True, max_age=7 * 24 * 3600)

        # Return the final response with tokens and user data.
        return response


# PROFILE VIEW
# This API view is responsible for returning the currently logged-in user's profile.
# RetrieveAPIView is used because this endpoint returns one single object.
class ProfileView(generics.RetrieveAPIView):

    # Use ProfileSerializer to control which user fields are shown in the response.
    serializer_class = ProfileSerializer

    # Only authenticated users can access this endpoint.
    # So the request must include a valid token.
    permission_classes = [IsAuthenticated]

    # Define which object should be returned by this retrieve view.
    def get_object(self):
        # Return the currently authenticated user.
        # request.user is automatically set by Django/DRF authentication system.
        return self.request.user