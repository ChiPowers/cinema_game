from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class HelloView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        content = {"message": "Hello, {} from Cinema!".format(request.user)}
        return Response(content)

    def get(self, request, format=None):
        content = {"message": "Hello, from Cinema!"}
        return Response(content)
