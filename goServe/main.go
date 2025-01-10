// Replacement for `python -m http.server` adapted from multiple sources:
//
// - https://gist.github.com/cubarco/0e129222b6e3946bf117
// - https://www.reddit.com/r/golang/comments/gxjkjy/comment/ft2pq54/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button
// - https://stackoverflow.com/a/13970713/3219667

package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
)

func main() {
	var port string
	var dir string
	flag.StringVar(&port, "port", "8000", "bind to this port (default: 8000)")
	flag.StringVar(&dir, "directory", ".", "serve this directory (default: current directory)")
	flag.Parse()

	fmt.Println(fmt.Sprintf("Serving files in the current directory on port %s", port))

	http.Handle("/", http.FileServer(http.Dir(dir)))
	err := http.ListenAndServe(":"+port, nil)
	if err != nil {
		log.Fatal("ListenAndServe: ", err)
	}
}
