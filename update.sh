
eval "$(ssh-agent -s)"

# Add your SSH key
ssh-add ~/.ssh/github-access

# Pull the latest changes from the repository
git pull

# Stop and remove the running containers
cd deploy
docker-compose down

# Go back to the root directory to build the Docker image
cd ..
docker build --no-cache -t backend .

# Go back to the deploy directory to restart the containers
cd deploy
docker-compose up -d

