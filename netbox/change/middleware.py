"""
The changes middleware checks whether we are in a change by checking the user
cookies. If we are, it adds signal handlers that fire before and after saving
a model to make sure we insert appropriate changes for them.

Some models are blacklisted to avoid recursion. This should probably be changed
to be a whitelist instead, since right now all Django models are captured as
well (TODO).
"""
from .models import ChangeSet


class FieldChangeMiddleware(object):
    """
    This  middleware checks whether we or someone else is in change and wires
    up the world accordingly. Its in-depth documentation can be found in the
    docs/ directory, because it's pretty gnarly.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # The change middleware is responsible for two custom attributes of the request object.
        # These are:
        #
        #   - request.foreign_changes:  holds a QuerySet of all foreign ongoing ChangeSets
        #   - request.my_change:    None or an actual ongoing change of the logged in user.

        # If the current user is anonymous, set the attributes manually to default state
        if request.user.is_anonymous:
            request.foreign_changes = None
            request.my_change = None
            return self.get_response(request)

        if request.user.has_perm('change.add_provisionset'):
            request.undeployed_changeset_count = ChangeSet.objects.exclude(status=ChangeSet.IMPLEMENTED) \
                .exclude(status=ChangeSet.IN_REVIEW) \
                .count()


        # Set request attributes
        request.foreign_changes = ChangeSet.objects.filter(active=True).exclude(user=request.user)
        request.my_change = request.user.changesets.filter(active=True).first()

        return self.get_response(request)
