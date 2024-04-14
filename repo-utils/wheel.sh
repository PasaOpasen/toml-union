
set -e

source get-python.sh

if [ ! -f setup.py ]
then
    echo "setup.py not found! exiting"
    exit 1
fi

$PYTHON setup.py develop
$PYTHON setup.py sdist
$PYTHON setup.py bdist_wheel
