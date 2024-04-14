#
# seeks for the Python interpreter in the parent directory
#
# exites with error if cannot found
#

cd ../

PYTHON=""
for python in "venv/bin/python" ".venv/bin/python" "python"
do
    if [ -x "$(command -v ${python})" ]
    then
        echo -e "Use python: $(which $python)"
        PYTHON=${python}
        break
    else
        echo "Not found python from ${python}"
    fi
done

if [ -z $PYTHON ]
then
    echo "Python interpreter not found!"
    exit 1
fi

