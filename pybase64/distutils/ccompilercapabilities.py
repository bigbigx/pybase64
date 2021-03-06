from distutils.errors import *
from distutils import log
import os
import sys

class CCompilerCapabilities:
    SIMD_SSSE3=0
    SIMD_SSE41=1
    SIMD_SSE42=2
    SIMD_AVX=3
    SIMD_AVX2=4
    SIMD_NEON32=5
    SIMD_NEON64=6

    def __init__(self, compiler):
        self.__capabilities = dict()
        self.__get_capabilities(compiler)

    def __has_simd_support(self, compiler, flags, include, content):
        quiet = True
        # this can't be included at module scope because it tries to
        # import math which might not be available at that point - maybe
        # the necessary logic should just be inlined?
        import tempfile
        fd, fname = tempfile.mkstemp(".c", "simd", text=True)
        f = os.fdopen(fd, "w")
        try:
            f.write("""#include <%s>\n""" % include)
            f.write("""\
int main (int argc, char **argv) {
    %s
}
""" % content)
        finally:
            f.close()

        if quiet:
            devnull = open(os.devnull, 'w')
            oldstderr = os.dup(sys.stderr.fileno())
            oldstdout = os.dup(sys.stdout.fileno())
            os.dup2(devnull.fileno(), sys.stderr.fileno())
            os.dup2(devnull.fileno(), sys.stdout.fileno())
        for flag in flags:
            lflags = []
            if not len(flag) == 0:
                lflags = [flag]
            try:
                objects = compiler.compile([fname], extra_postargs=lflags)
            except CompileError:
                continue
            try:
                compiler.link_executable(objects, "a.out")
            except (LinkError, TypeError):
                continue
            if quiet:
                os.dup2(oldstderr, sys.stderr.fileno())
                os.dup2(oldstdout, sys.stdout.fileno())
                devnull.close()
            return { 'support': True, 'flags': lflags }
        if quiet:
            os.dup2(oldstderr, sys.stderr.fileno())
            os.dup2(oldstdout, sys.stdout.fileno())
            devnull.close()
        return { 'support': False, 'flags': [] }

    def __get_capabilities(self, compiler):
        log.info("getting compiler simd support")
        self.__capabilities[CCompilerCapabilities.SIMD_SSSE3] = self.__has_simd_support(compiler, ['','-mssse3'], 'tmmintrin.h', '__m128i t = _mm_setzero_si128(); t = _mm_shuffle_epi8(t, t); return _mm_cvtsi128_si32(t);')
        log.info("SSSE3: %s" % str(self.__capabilities[CCompilerCapabilities.SIMD_SSSE3]['support']))
        self.__capabilities[CCompilerCapabilities.SIMD_SSE41] = self.__has_simd_support(compiler, ['','-msse4.1'], 'smmintrin.h', '__m128i t = _mm_setzero_si128(); t = _mm_insert_epi32(t, 1, 1); return _mm_cvtsi128_si32(t);')
        log.info("SSE41: %s" % str(self.__capabilities[CCompilerCapabilities.SIMD_SSE41]['support']))
        self.__capabilities[CCompilerCapabilities.SIMD_SSE42] = self.__has_simd_support(compiler, ['','-msse4.2'], 'nmmintrin.h', '__m128i t = _mm_setzero_si128(); return _mm_cmpistra(t, t, 0);')
        log.info("SSE42: %s" % str(self.__capabilities[CCompilerCapabilities.SIMD_SSE42]['support']))
        self.__capabilities[CCompilerCapabilities.SIMD_AVX]   = self.__has_simd_support(compiler, ['','-mavx'],   'immintrin.h', '__m256i t = _mm256_setzero_si256(); return _mm_cvtsi128_si32(_mm256_castsi256_si128(t));')
        log.info("AVX:   %s" % str(self.__capabilities[CCompilerCapabilities.SIMD_AVX]['support']))
        self.__capabilities[CCompilerCapabilities.SIMD_AVX2]  = self.__has_simd_support(compiler, ['','-mavx2'],  'immintrin.h', '__m256i t = _mm256_broadcastd_epi32(_mm_setzero_si128()); return _mm_cvtsi128_si32(_mm256_castsi256_si128(t));')
        log.info("AVX2:  %s" % str(self.__capabilities[CCompilerCapabilities.SIMD_AVX2]['support']))

    def has(self, what):
        if not what in self.__capabilities:
            return False
        return self.__capabilities[what]['support']

    def flags(self, what):
        if not self.has(what):
            return self.__capabilities[666]['flags']
        return self.__capabilities[what]['flags']
