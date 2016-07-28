
die() {
    echo "$0: die - $*" >&2
    exit 1
}

[ -z "$1" ] && die "Usage: $0 <ipynb>"
[ ! -f "$1" ] && die "Error no such file as '$1'
Usage: $0 <ipynb>"

jupyter nbconvert --template full --to slides --stdout "$1" > SLIDES.html

PORT=8001
echo
echo "Starting web server on port $PORT"
echo "Connect to http://localhost:${PORT}/SLIDES.html?print-pdf and then print"
python2 -m SimpleHTTPServer $PORT


