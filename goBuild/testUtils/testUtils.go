package testUtils

import (
	"bytes"
	"io"
	"os"
)

// Decide if two files have the same contents or not.
// chunkSize is the size of the blocks to scan by; pass 0 to get a sensible default.
// *Follows* symlinks.
//
// May return an error if something else goes wrong; in this case, you should ignore the value of 'same'.
//
// Copied from https://stackoverflow.com/a/73411967/3219667
// under CC-BY-SA-4.0 by several contributors
func FileCmp(file1, file2 string, chunkSize int) (same bool, err error) {

	if chunkSize == 0 {
		chunkSize = 4 * 1024
	}

	// shortcuts: check file metadata
	stat1, err := os.Stat(file1)
	if err != nil {
		return false, err
	}

	stat2, err := os.Stat(file2)
	if err != nil {
		return false, err
	}

	// are inputs are literally the same file?
	if os.SameFile(stat1, stat2) {
		return true, nil
	}

	// do inputs at least have the same size?
	if stat1.Size() != stat2.Size() {
		return false, nil
	}

	// long way: compare contents
	f1, err := os.Open(file1)
	if err != nil {
		return false, err
	}
	defer f1.Close()

	f2, err := os.Open(file2)
	if err != nil {
		return false, err
	}
	defer f2.Close()

	b1 := make([]byte, chunkSize)
	b2 := make([]byte, chunkSize)
	for {
		n1, err1 := io.ReadFull(f1, b1)
		n2, err2 := io.ReadFull(f2, b2)

		// https://pkg.go.dev/io#Reader
		// > Callers should always process the n > 0 bytes returned
		// > before considering the error err. Doing so correctly
		// > handles I/O errors that happen after reading some bytes
		// > and also both of the allowed EOF behaviors.

		if !bytes.Equal(b1[:n1], b2[:n2]) {
			return false, nil
		}

		if (err1 == io.EOF && err2 == io.EOF) || (err1 == io.ErrUnexpectedEOF && err2 == io.ErrUnexpectedEOF) {
			return true, nil
		}

		// some other error, like a dropped network connection or a bad transfer
		if err1 != nil {
			return false, err1
		}
		if err2 != nil {
			return false, err2
		}
	}
}
