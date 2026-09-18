from rest_framework import permissions


class IsProfileOwnerOrReadOnly(permissions.BasePermission):
    """Редагувати профіль може лише його власник, читати — будь-хто автентифікований."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user
