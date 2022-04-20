# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import copy
from enum import Enum
import mongoengine as me

from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE
from st2common.constants.types import ResourceType
from st2common.fields import ComplexDateTimeField
from st2common.models.db import stormbase
from st2common.rbac.backends import get_rbac_backend
from st2common.util import date as date_utils

__all__ = ["UserDB", "TokenDB", "ApiKeyDB", "SSORequestDB"]


class UserDB(stormbase.StormFoundationDB):
    """
    An entity representing system user.

    Attribute:
        name: Username. Also used as a primary key and foreign key when referencing users in other
              models.
        is_service: True if this is a service account.
        nicknames: Nickname + origin pairs for ChatOps auth.
    """

    name = me.StringField(required=True, unique=True)
    is_service = me.BooleanField(required=True, default=False)
    nicknames = me.DictField(
        required=False, help_text='"Nickname + origin" pairs for ChatOps auth'
    )

    def get_roles(self, include_remote=True):
        """
        Retrieve roles assigned to that user.

        :param include_remote: True to also include remote role assignments.
        :type include_remote: ``bool``

        :rtype: ``list`` of :class:`RoleDB`
        """
        rbac_service = get_rbac_backend().get_service_class()
        result = rbac_service.get_roles_for_user(
            user_db=self, include_remote=include_remote
        )
        return result

    def get_permission_assignments(self):
        # TODO
        pass


class TokenDB(stormbase.StormFoundationDB):
    """
    An entity representing an access token.

    Attribute:
        user: Reference to the user this token belongs to (username).
        token: Random access token.
        expiry: Date when this token expires.
        service: True if this is a service (system) token.
    """

    user = me.StringField(required=True)
    token = me.StringField(required=True, unique=True)
    expiry = me.DateTimeField(required=True)
    metadata = me.DictField(
        required=False, help_text="Arbitrary metadata associated with this token"
    )
    service = me.BooleanField(required=True, default=False)

class SSORequestDB(stormbase.StormFoundationDB):

    class Type(Enum):
        CLI = 'cli'
        WEB = 'web'
    
    """
    An entity representing a SSO request.

    Attribute:
        request_id: Reference to the SSO request unique ID
        expiry: Time at which this request expires.
        type: What type of SSO request is this? web/cli 

        -- cli --
        key: Symmetric key used to encrypt/decrypt contents from/to the CLI.
    """

    request_id = me.StringField(required=True)
    key = me.StringField(required=False, unique=False)
    expiry = me.DateTimeField(required=True)
    type = me.EnumField(Type, required=True)
    

class ApiKeyDB(stormbase.StormFoundationDB, stormbase.UIDFieldMixin):
    """
    An entity representing an API key object.

    Each API key object is scoped to the user and inherits permissions from that user.
    """

    RESOURCE_TYPE = ResourceType.API_KEY
    UID_FIELDS = ["key_hash"]

    user = me.StringField(required=True)
    key_hash = me.StringField(required=True, unique=True)
    metadata = me.DictField(
        required=False, help_text="Arbitrary metadata associated with this token"
    )
    created_at = ComplexDateTimeField(
        default=date_utils.get_datetime_utc_now,
        help_text="The creation time of this ApiKey.",
    )
    enabled = me.BooleanField(
        required=True,
        default=True,
        help_text="A flag indicating whether the ApiKey is enabled.",
    )

    meta = {"indexes": [{"fields": ["user"]}, {"fields": ["key_hash"]}]}

    def __init__(self, *args, **values):
        super(ApiKeyDB, self).__init__(*args, **values)
        self.uid = self.get_uid()

    def mask_secrets(self, value):
        result = copy.deepcopy(value)

        # In theory the key_hash is safe to return as it is one way. On the other
        # hand given that this is actually a secret no real point in letting the hash
        # escape. Since uid contains key_hash masking that as well.
        result["key_hash"] = MASKED_ATTRIBUTE_VALUE
        result["uid"] = MASKED_ATTRIBUTE_VALUE
        return result


MODELS = [UserDB, TokenDB, ApiKeyDB, SSORequestDB]
