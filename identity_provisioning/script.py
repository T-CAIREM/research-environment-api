import schemas
import services

user = {"userName": "test", "familyName": "Szuster", "givenName": "Karol"}
cloud_identity = schemas.CloudIdentityCreation().load(user)

cloud_identity = services._recover_or_persist_cloud_identity(cloud_identity)
print(cloud_identity)
