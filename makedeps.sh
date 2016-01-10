rm -r ./build
rm -r ./dist
python setup.py build
mv build/lib.linux-x86_64-3.5/hashes.cpython-35m-x86_64-linux-gnu.so .
