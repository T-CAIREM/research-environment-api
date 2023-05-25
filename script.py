from research_environment_api.library.google.workspace import *
from research_environment_api.library.google.billing import *

from research_environment_api.modules.billing_management.services import *

from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    "/Users/kshalot/Upside/t-cairem/research-environment-api/research-environment-api-dev-584932fd02e8.json"
)

# parent = "policies/cloudresourcemanager.googleapis.com%2Fprojects%2Fresearch-environment-api-dev/denypolicies"

# print(
#     list_iam_policies(credentials, "3105849901", "karoldev@healthdatanexus.ai", "resource://cloudbilling.googleapis.com/billingAccounts")
# )

# print(get_user(credentials, {"user_name": "karoldev@healthdatanexus.ai"}))
print(get_user(credentials, "karoldev@healthdatanexus.ai"))
# print(
#     get_iam_policy_for_billing_account(
#         credentials,
#         billing_account_resource_name="billingAccounts/011521-80DB62-FE7EA2",
#     )
# )

# print(
#     create_membership_binding_for_billing_account(
#         credentials,
#         "billingAccounts/011521-80DB62-FE7EA2",
#         "karolszuster@test.com",
#     )
# )

# print(
#     x := list_billing_accounts(
#         credentials,
#         "karoldev@healthdatanexus.ai",
#         "3105849901",
#     )
# )

# x = list_billing_accounts_for(credentials, "3105849901", "karoldev@healthdatanexus.ai")
# print(x)

# print(list(x)[0].policy.bindings[0].members)

# print(
#     list_iam_policies(
#         credentials,
#         "karoldev@healthdatanexus.ai",
#         "3105849901",
#         "resource://cloudbilling.googleapis.com/billingAccounts",
#     )
# )
