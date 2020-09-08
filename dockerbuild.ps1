$version="v0.1.0"

docker build . -t hub.global.cloud.sap/monsoon/arista-service-discovery:${version}
docker push hub.global.cloud.sap/monsoon/arista-service-discovery:${version}

docker build . -t keppel.eu-de-1.cloud.sap/ccloud/arista-service-discovery:${version}
docker push keppel.eu-de-1.cloud.sap/ccloud/arista-service-discovery:${version}
