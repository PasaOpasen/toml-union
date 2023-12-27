#
# example of how to run this tests using docker image
#
#

container=TOML_UNION
IMAGE=pasaopasen/toml-union
target=./tmp/out

#
# remove previous container
#
docker container rm ${container} 2> /dev/null  || true

#
# mount and run
#
docker run -it --name ${container}  \
    -v "$(pwd)"/input:/toml_union/input \
    ${IMAGE} \
    python toml_union.py ./input -o /out/output.toml -r /out/report.json \
        -k tool.poetry.name=union \
        -k tool.poetry.version=12

#
# remove previous output
#

rm -rf $target

#
# extract output
#

mkdir -p "$(dirname "$target")"
docker cp ${container}:/out $target

echo "Results in ${target}:"
ls -lah $target

echo -e '\n\n'

report=${target}/report.json
if [ -f "${report}" ]
then
    echo there r some toml conflicts, take a look at file ${report}
else
    echo no conflicts
fi
