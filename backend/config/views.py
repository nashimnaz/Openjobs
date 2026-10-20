import logging
from django.db import connection
from django.db.utils import OperationalError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Health check endpoint reporting application and database connectivity.
    Guarantees no sensitive credentials, secrets, or internal details are exposed.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        db_status = "healthy"
        http_status = status.HTTP_200_OK

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
        except OperationalError as exc:
            logger.error("Database connectivity check failed: %s", exc)
            db_status = "unreachable"
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        except Exception as exc:
            logger.error("Unexpected error during database check: %s", exc)
            db_status = "error"
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(
            {
                "status": "healthy" if db_status == "healthy" else "degraded",
                "database": db_status,
                "service": "openjobs-backend",
            },
            status=http_status,
        )
