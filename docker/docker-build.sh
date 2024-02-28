#!/usr/bin/env bash

#############################################################################################################
[ -n "$ACTION" ]                 || ACTION=build



[ -z "$DOCKER_IMAGETAG" ]        && DOCKER_IMAGETAG=latest
# [ -z "$DOCKER_VERSIONTAG" ]      && DOCKER_VERSIONTAG="1.0"

[ -z "$DOCKER_REGISTRY" ]        && DOCKER_REGISTRY="docker.io"

[ -z "$DOCKER_FILE" ]            && DOCKER_FILE=Dockerfile
[ -z "$DOCKER_MULTIARCH"]        && DOCKER_MULTIARCH=0

[ -z "$SOURCE_TYPE" ]            && SOURCE_TYPE=git 
[ -z "$SOURCE_BRANCH" ]          && SOURCE_BRANCH=$(git symbolic-ref -q --short HEAD)  

[ -z "$GIT_SHA1" ]               && GIT_SHA1=$(git rev-parse -q HEAD)
[ -z "$GIT_SHA1_SHORT" ]         && GIT_SHA1_SHORT=$(git rev-parse --short HEAD)
[ -z "$GIT_VERSION" ]            && GIT_VERSION="$(git describe --long --tags)"

#############################################################################################################
# In case git isn't initialized
[ -z "$SOURCE_BRANCH" ]          && SOURCE_BRANCH="main"
# [ -z "$DOCKER_VERSIONTAG" ]      && DOCKER_VERSIONTAG="0.0.1"
# [ -z "$GIT_VERSION" ]            && GIT_VERSION="0.0.1"

#############################################################################################################
#############################################################################################################
function show_info() {
    echo "Docker Build Script v1.0 (sanderson@eye-catcher.com)"
    echo 
}

function show_help() {
    # Display Help
    echo 
    echo "Syntax: docker-build.sh [-h|a|t|p|m]"
    echo "options:"
    echo "  h   Display Help"
    echo "  a   Action (build, publish, build-publish)"

    echo "  f   Docker file name for build (default $DOCKER_FILE)"
    echo "  t   Specify a Docker Image Tag  (default: $DOCKER_IMAGETAG)"
    echo "  v   Specify a Docker Version Tag (default: $DOCKER_VERSIONTAG)"
    echo "  m   Enable docker multi-arch build"
}

function parse_yaml {
   local prefix=$2
   local s='[[:space:]\-]*' w='[a-zA-Z0-9_\-]*' fs=$(echo @|tr @ '\034')
   sed -ne "s|^\($s\):|\1|" \
        -e "s|^\($s\)\($w\)$s[:=]$s[\"']\(.*\)[\"']$s\$|\1$fs\2$fs\3|p" \
        -e "s|^\($s\)\($w\)$s[:=]$s\(.*\)$s\$|\1$fs\2$fs\3|p"  $1 |
   awk -F$fs '{
      indent = length($1)/2;
      vname[indent] = $2;
      for (i in vname) {if (i > indent) {delete vname[i]}}
      if (length($3) > 0) {
         vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])("_")}
         printf("export %s%s%s=\"%s\"\n", "'$prefix'",vn, $2, $3);
      }
   }'
}

function load_jenkins_vars()
{
    if [ -f "jenkins-vars.yml" ]; then
        echo "Reading jenkins-vars.yml..."
        eval $(parse_yaml jenkins-vars.yml "jenkins_vars_")
        
        [[ -n "$jenkins_vars_release_tag" ]]                  && DOCKER_IMAGETAG=$jenkins_vars_release_tag
        [[ -n "$jenkins_vars_repo_vars__REGISTRY" ]]          && DOCKER_REGISTRY=$jenkins_vars_repo_vars__REGISTRY
        [[ -n "$jenkins_vars_repo_vars__CONTAINER_NAME" ]]    && DOCKER_IMAGENAME=$jenkins_vars_repo_vars__CONTAINER_NAME
        [[ -n "$jenkins_vars_repo_vars__MULTIARCH" ]]         && DOCKER_MULTIARCH=$jenkins_vars_repo_vars__MULTIARCH
        [[ -n "$jenkins_vars_repo_vars__LS_USER" ]]           && DOCKER_LIBRARY=$jenkins_vars_repo_vars__LS_USER
    fi
}

function load_env_vars()
{
    if [ -f ".env" ]; then
        echo "Not implemented..."
    fi
}


#############################################################################################################
#############################################################################################################
show_info
load_jenkins_vars

while getopts "ha:i:r:u:f:t:p:v:m" option; do
    case $option in 
        h) # Display help
            show_help
            exit;;
        a) # Set action
            ACTION=$OPTARG;;
        i) # Docker Image Name
            echo "Setting custom image name: $OPTARG"
            DOCKER_IMAGENAME=$OPTARG;;
        r) # Docker Repo Name
            echo "Setting custom repo name: $OPTARG"
            DOCKER_LIBRARY=$OPTARG;;
        u) # Docker Registry Base URL
            echo "Setting custom registry name: $OPTARG"
            DOCKER_REGISTRY=$OPTARG;;
        f) # Docker File Name
            echo "Setting custom docker file: $OPTARG"
            DOCKER_FILE=$OPTARG;;
        t) # Docker Image Tag
            echo "Setting custom docker image tag: $OPTARG"
            DOCKER_IMAGETAG=$OPTARG;;
        v) # Docker Version Tag
            echo "Setting docker version tag: $OPTARG"
            VERSION=$OPTARG;;

        m) # Docker Multi-arch build
            echo "Setting docker multi arch build"
            DOCKER_MULTIARCH=1;;
        \?) # Invalid Option
            #echo "Error: Invalid Option"
            show_help
            exit;;
    esac
done

#############################################################################################################

[[ -z "$VERSION" && -n "$GIT_VERSION" ]] && VERSION=$GIT_VERSION
[[ -z "$VERSION" && -n "$DOCKER_VERSION" ]] && VERSION=$DOCKER_VERSION

[[ -z "$VERSION" ]] && VERSION="0.0.1"

#############################################################################################################

echo "Active settings:"
echo "  Docker Action      : ${ACTION}"

echo "  Docker Image Tag   : ${DOCKER_IMAGETAG}"
echo "  Docker Version Tag : ${DOCKER_VERSIONTAG}"
echo "  Docker Multiarch   : ${DOCKER_MULTIARCH}"
echo "  Git Branch : ${SOURCE_BRANCH}"
echo "  Git Version: ${GIT_VERSION}"
echo "  Git SHA1   : ${GIT_SHA1_SHORT}"
echo ""

#############################################################################################################

function docker_build()
{
    local docker_file=$1
    local docker_context=$2
    local image_name=$3
    local image_tag=$4
    local image_tag_version=$5
    local image_tag_sha1=$6
    
    shift 6
    local env_args=($@)
    
    [[ "$DOCKER_MULTIARCH" == "1" || "$DOCKER_MULTIARCH" == "true" ]] && build_mode="buildx build --load " || build_mode="build"
    #build_mode="build"

    local build_args=""
    for i in "${env_args[@]}"
    do
        build_args+="--build-arg $i "
    done

    echo "Building Image: $image_name"

    tar -czh $docker_context | docker \
        $build_mode \
        {$debug:+--progress plain} \
        --network host \
        --no-cache \
        --force-rm \
        --build-arg SOURCE_COMMIT=$GIT_SHA1 \
        --build-arg SOURCE_TYPE=$SOURCE_TYPE ${build_args:-} \
        ${image_tag_version:+--build-arg VERSION=$image_tag_version} \
        ${docker_file:+--file $docker_file} \
        --tag $image_name \
        ${image_tag:+--tag $image_name:$image_tag} \
        ${image_tag_version:+--tag $image_name:$image_tag_version} \
        ${image_tag_sha1:+--tag $image_name:$image_tag_sha1} \
        -
}

function docker_publish()
{
    local image_name=$1
    local image_tag=$2
    local image_tag_version=$3
    local image_tag_commit_sha=$4
    local image_registry=$5

    echo "Publishing Image: $image_name"

    tagCount=0
    [ -n "$image_tag" ] && { ((tagCount+=1)); echo "Pushing image tag"; docker push $image_name:$image_tag; }
    [ -n "$image_tag_version" ] && { ((tagCount+=1)); echo "Pushing version tag"; docker push $image_name:$image_tag_version; }
    [ -n "$image_tag_commit_sha" ] && { ((tagCount+=1)); echo "Pushing commit sha tag"; docker push $image_name:$image_tag_commit_sha; }
    [[ $tagCount > 0 ]] && { echo "Pushing all tags"; docker push $image_name --all-tags; }

    if [[ -f "README.MD" || -f "README.md" ]]; then
        pushrm_provider="--provider dockerhub"

        [[ $image_registry == *"harbor"* ]] && pushrm_provider="--provider harbor2"
        [[ $image_registry == *"quay"* ]] && pushrm_provider="--provider quay"

        echo "Publishing Image Readme"
        docker pushrm $image_name:$image_tag $pushrm_provider
    fi
}

#############################################################################################################

if [[ "$ACTION" == *"build"* ]]; then

    docker_build \
        "Dockerfile" \
        "." \
        "ravensorb/pmm-cfg-gen" \
        "$DOCKER_IMAGETAG" \
        "$VERSION" \
        "$GIT_SHA1_SHORT" 
fi

if [[ "$ACTION" == *"publish"* ]]; then

    docker_publish \
        "ravensorb/pmm-cfg-gen" \
        "$DOCKER_IMAGETAG" \
        "$VERSION" \
        "$GIT_SHA1_SHORT" \
        "$DOCKER_REGISTRY"
fi