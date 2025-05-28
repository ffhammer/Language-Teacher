( for file in src/**.py *.py; do
    echo "==== $file ===="
    cat "$file"
    echo
done ) | pbcopy