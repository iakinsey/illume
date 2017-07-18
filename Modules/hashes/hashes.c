/* hashes.c
 * 
 * Utilizes the Fowler-Noll-Vo 1a hash function to generate a set of
 * non-cryptographic hashes that can be used for a bloom filter.
 * 
 * FNV1a is a hash algorithm optimized for speed of computation and avalanche
 * characteristics.
 *
 * More info on the FNV hashing algorithm be found here:
 * http://www.isthe.com/chongo/tech/comp/fnv/index.html
 * https://en.wikipedia.org/wiki/Fowler%E2%80%93Noll%E2%80%93Vo_hash_function
 * 
 * The composite hash works by computing the two independent hash functions
 * h1(x) and h2(x) and creating a set of results from the values k and m, where
 * k is the number of hash functions.
 *
 * The equation noted by Kirsch and Mitzenmacher is as follows:
 *
 * g(x) = (h1(x) + i*h2(x) + i^2) % m
 *
 * The value of pow(i, 2) is added to their sum, where i ranges from 0 up to
 * some number k - 1. The result modulo m is computed, where m is the size of
 * the hash table.
 *
 * Generally, the value of k is represented by some set of independent hash
 * functions for a bloom filter. In this case, the hashing is only performed
 * once, using FNV1a. The upper and lower 32-bit values of the 64-bit FNV1a
 * digest simulate the result of 2 hash functions h1(x) and h2(x). This was
 * initially noted by Will Fitzgerald.
 *
 * Upper/lower hash Will Fitzgerland: 
 * https://willwhim.wpengine.com/2011/09/03/producing-n-hash-functions-by-hashing-only-once/
 *
 * Kirsch and Mitzenmacher found that only two hash functions were needed:
 * https://www.eecs.harvard.edu/~michaelm/postscripts/rsa2008.pdf
**/


#include "fnv/fnv.h"
#include <python3.6m/Python.h>
#include <math.h>


#define ONES_64 0xFFFFFFFFLL


static PyObject * fnv1a64_composite_from_str(PyObject* self, PyObject* args);
static PyObject * fnv1a64_composite_from_iter(PyObject* self, PyObject* args);
static PyObject * digest_composite_fnv1a64(char *content, int k, int m);
Fnv32_t get_composite(Fnv64_t hashval, int i, int m);
Fnv32_t get_upper(Fnv64_t hashval);
Fnv32_t get_lower(Fnv64_t hashval);


/**
 * get_upper - Gets the upper 32 bits of a 64 bit integer.
 * @ hashval - A 64 bit integer.
 */
Fnv32_t get_upper(Fnv64_t hashval) {
    return hashval & ONES_64;
}


/**
 * get_lower - Gets the lower 32 bits of a 64 bit integer.
 * @ hashval - A 64 bit integer.
 */
Fnv32_t get_lower(Fnv64_t hashval) {
    return (hashval >> 32) & ONES_64;
}


/**
 * get_composite - Given a 64-bit hash value, return the composite key at value
 * i within range m.
 *
 * @ hashval - A 64 bit integer.
 * @ i - Composite hash index.
 * @ m - Maximum value for hash.
 *                  
 */
Fnv32_t get_composite(Fnv64_t hashval, int i, int m) {
    Fnv32_t i2 = (Fnv32_t) i;
    Fnv32_t lower = get_lower(hashval);
    Fnv32_t upper = get_upper(hashval);
    Fnv32_t index = (Fnv32_t) pow(i, 2);
    Fnv32_t mod = (Fnv32_t) mod;
    
    return (lower + (i2 * upper) + index) % m;
}


/**
 * digest_composite_fnv1a64 - Return composite hash of content.
 * @ content - Content to be hashed.
 * @ k - Number of composite hashes to generate.
 * @ m - Maximum value for hash.
 *                  
 */
static PyObject * digest_composite_fnv1a64(char *content, int k, int m) {
    PyObject * hashes = PyList_New(k);
    Fnv64_t hashval = fnv_64_str(content, FNV1_64_INIT);

    while (k--) {
        PyList_SetItem(
            hashes,
            k,
            PyLong_FromUnsignedLong(get_composite(hashval, k, m))
        );
    }

    return hashes;
}

/**
 *  fnv1a64_composite_from_str - Wraps digest_composite_fnv1a64 for use by the
 *  python interpreter
 */

static PyObject * fnv1a64_composite_from_str(PyObject* self, PyObject* args) {
    int k;
    int m; 
    char *content;

    if (!PyArg_ParseTuple(args, "sii", &content, &k, &m)) {
        PyErr_SetString(PyExc_ValueError, "Argument scheme \"sii\" required");
        return NULL;
    }

    if (k == 0) {
        PyErr_SetString(PyExc_ValueError, "Value of k must be greater than 0");
        return NULL;
    }

    return digest_composite_fnv1a64(content, k, m);
}


static PyMethodDef Methods[] = {
    {
        "fnv1a64_composite", 
        fnv1a64_composite_from_str, 
        METH_VARARGS,
        "Get a composite fnv1a64 hash"
    }
};


static PyModuleDef hashes_module = {
    PyModuleDef_HEAD_INIT,
    "hashes",
    NULL,
    -1,
    Methods
};


PyMODINIT_FUNC PyInit_hashes(void) {
    return PyModule_Create(&hashes_module);
}
