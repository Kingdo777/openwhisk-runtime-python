#!/bin/bash

# Run `git clone https://github.com/Kingdo777/ChestBox.git` for getting the project.
ProjectRoot=$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")

sh -c "$ProjectRoot/tools/update-packages.sh"

./gradlew :core:python310Action:distDocker -PdockerImagePrefix=kingdo -PdockerRegistry=docker.io
#./gradlew :core:python27Action:distDocker -PdockerImagePrefix=kingdo -PdockerRegistry=docker.io