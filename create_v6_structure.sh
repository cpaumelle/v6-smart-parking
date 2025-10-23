#!/bin/bash
# create_v6_structure.sh

# Create the main project directory structure
sudo mkdir -p v6_smart_parking/{backend,frontend,migrations,scripts,deployment,docs,tests}
sudo mkdir -p v6_smart_parking/backend/{src,tests,alembic}
sudo mkdir -p v6_smart_parking/backend/src/{core,services,routers,models,utils,middleware,schemas,exceptions}
sudo mkdir -p v6_smart_parking/backend/src/routers/{v5_compat,v6,auth,health}
sudo mkdir -p v6_smart_parking/frontend/src/{components,services,hooks,utils,config}
sudo mkdir -p v6_smart_parking/tests/{unit,integration,load,e2e}
sudo mkdir -p v6_smart_parking/config/{chirpstack,mosquitto,traefik}

# Create placeholder files
sudo touch v6_smart_parking/.env.example
sudo touch v6_smart_parking/docker-compose.yml
sudo touch v6_smart_parking/backend/requirements.txt
sudo touch v6_smart_parking/backend/Dockerfile
sudo touch v6_smart_parking/frontend/package.json
sudo touch v6_smart_parking/frontend/Dockerfile

echo "✅ V6 project structure created!"
