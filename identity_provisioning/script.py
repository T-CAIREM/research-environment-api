import schemas
import services

user = {"userName": "karol.szuster", "familyName": "Szuster", "givenName": "Karol"}
cloud_identity = schemas.CloudIdentityCreation().load(user)

# cloud_identity = services._persist_cloud_identity(cloud_identity)
cloud_identity = services.provision_cloud_identity(cloud_identity)
print(cloud_identity)
