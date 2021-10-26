from tortoise.models import Model
from tortoise import fields
from uuid import uuid4


class Server(Model):
    """A class representing a server model in the database"""

    # This is how you set metadata in Tortoise, I do not fancy this
    class Meta:
        table = "servers"  # Setting a custom table name

    id = fields.TextField(default=lambda: str(uuid4()), pk=True)
    """A unique ID for the server. It will be a UUID"""

    ip = fields.CharField(null=False, unique=True, max_length=15)
    """The IPv4 address of the server. It cannot go above 15 characters because it's an IPv4"""

    description = fields.TextField(null=False)
    """The server's description. Can be found upon pinging it"""

    latency = fields.FloatField(null=False)
    """The latency from the client to the server during the scan/update"""

    version = fields.CharField(null=False, max_length=255)
    """The version of the server software"""

    players_max = fields.IntField(null=False)
    """Maximum players allowed online at the same time on that server"""

    players_online = fields.IntField(null=False)
    """Number of players online on the server during the scan/update"""

    updated_at = fields.BigIntField(null=False)
    """When the server was last updated at. It's a UNIX Epoch timestamp"""
