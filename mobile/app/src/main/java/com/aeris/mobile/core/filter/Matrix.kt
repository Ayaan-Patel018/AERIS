package com.aeris.mobile.core.filter

import kotlin.math.abs

/**
 * A simple row-major dense matrix of [Double] values.
 *
 * Provides the linear-algebra primitives required by the Error-State EKF
 * without pulling in an external math library:
 * - Addition, subtraction, scalar multiplication
 * - Matrix–matrix and matrix–vector multiplication
 * - Transpose
 * - General inverse via Gauss-Jordan elimination (for small matrices
 *   such as the 3×3 or 6×6 innovation matrices)
 * - Identity and zero factories
 *
 * This class is intentionally kept minimal and allocation-friendly for
 * hot-path usage at ~100 Hz; no object pooling is used (the JVM's
 * escape analysis handles short-lived matrices well enough).
 */
class Matrix(
    /** Number of rows. */
    val rows: Int,
    /** Number of columns. */
    val cols: Int,
    /** Row-major data array. Length must equal [rows] × [cols]. */
    val data: DoubleArray = DoubleArray(rows * cols)
) {

    init {
        require(data.size == rows * cols) {
            "Data array size ${data.size} does not match ${rows}x${cols} = ${rows * cols}"
        }
    }

    /** Element access (row, col), zero-indexed. */
    operator fun get(row: Int, col: Int): Double = data[row * cols + col]

    /** Element mutation (row, col), zero-indexed. */
    operator fun set(row: Int, col: Int, value: Double) {
        data[row * cols + col] = value
    }

    /** Returns a deep copy. */
    fun copy(): Matrix = Matrix(rows, cols, data.copyOf())

    // ── Arithmetic ──────────────────────────────────────────────────────

    /** Element-wise addition. Both matrices must have the same shape. */
    operator fun plus(other: Matrix): Matrix {
        require(rows == other.rows && cols == other.cols) { "Shape mismatch" }
        val result = DoubleArray(data.size)
        for (i in result.indices) result[i] = data[i] + other.data[i]
        return Matrix(rows, cols, result)
    }

    /** Element-wise subtraction. */
    operator fun minus(other: Matrix): Matrix {
        require(rows == other.rows && cols == other.cols) { "Shape mismatch" }
        val result = DoubleArray(data.size)
        for (i in result.indices) result[i] = data[i] - other.data[i]
        return Matrix(rows, cols, result)
    }

    /** Scalar multiplication. */
    operator fun times(scalar: Double): Matrix {
        val result = DoubleArray(data.size)
        for (i in result.indices) result[i] = data[i] * scalar
        return Matrix(rows, cols, result)
    }

    /** Matrix–matrix multiplication (this × other). */
    operator fun times(other: Matrix): Matrix {
        require(cols == other.rows) {
            "Cannot multiply ${rows}x${cols} by ${other.rows}x${other.cols}"
        }
        val result = DoubleArray(rows * other.cols)
        for (i in 0 until rows) {
            for (j in 0 until other.cols) {
                var sum = 0.0
                for (k in 0 until cols) {
                    sum += this[i, k] * other[k, j]
                }
                result[i * other.cols + j] = sum
            }
        }
        return Matrix(rows, other.cols, result)
    }

    /** Matrix–vector multiplication. Vector length must equal [cols]. */
    fun multiplyVector(v: DoubleArray): DoubleArray {
        require(v.size == cols) { "Vector size ${v.size} != cols $cols" }
        val result = DoubleArray(rows)
        for (i in 0 until rows) {
            var sum = 0.0
            for (j in 0 until cols) {
                sum += this[i, j] * v[j]
            }
            result[i] = sum
        }
        return result
    }

    /** Transpose. */
    fun transpose(): Matrix {
        val result = DoubleArray(rows * cols)
        for (i in 0 until rows) {
            for (j in 0 until cols) {
                result[j * rows + i] = this[i, j]
            }
        }
        return Matrix(cols, rows, result)
    }

    // ── Inverse ─────────────────────────────────────────────────────────

    /**
     * Computes the inverse of a square matrix using Gauss-Jordan elimination
     * with partial pivoting.
     *
     * @throws IllegalArgumentException if the matrix is not square.
     * @throws ArithmeticException if the matrix is singular (within [tol]).
     */
    fun inverse(tol: Double = 1e-12): Matrix {
        require(rows == cols) { "Cannot invert non-square matrix ${rows}x${cols}" }
        val n = rows

        // Augmented matrix [A | I].
        val aug = Matrix(n, 2 * n)
        for (i in 0 until n) {
            for (j in 0 until n) aug[i, j] = this[i, j]
            aug[i, n + i] = 1.0
        }

        for (col in 0 until n) {
            // Partial pivot: find row with largest absolute value in column.
            var maxVal = abs(aug[col, col])
            var maxRow = col
            for (row in col + 1 until n) {
                val v = abs(aug[row, col])
                if (v > maxVal) { maxVal = v; maxRow = row }
            }
            if (maxVal < tol) {
                throw ArithmeticException("Singular matrix at column $col (pivot $maxVal < $tol)")
            }

            // Swap rows.
            if (maxRow != col) {
                for (j in 0 until 2 * n) {
                    val tmp = aug[col, j]
                    aug[col, j] = aug[maxRow, j]
                    aug[maxRow, j] = tmp
                }
            }

            // Scale pivot row.
            val pivot = aug[col, col]
            for (j in 0 until 2 * n) aug[col, j] /= pivot

            // Eliminate column in all other rows.
            for (row in 0 until n) {
                if (row == col) continue
                val factor = aug[row, col]
                for (j in 0 until 2 * n) {
                    aug[row, j] -= factor * aug[col, j]
                }
            }
        }

        // Extract inverse from the right half.
        val inv = Matrix(n, n)
        for (i in 0 until n) {
            for (j in 0 until n) {
                inv[i, j] = aug[i, n + j]
            }
        }
        return inv
    }

    /**
     * Extracts a sub-matrix from row [r0] (inclusive) to [r1] (exclusive)
     * and column [c0] (inclusive) to [c1] (exclusive).
     */
    fun subMatrix(r0: Int, r1: Int, c0: Int, c1: Int): Matrix {
        val sr = r1 - r0
        val sc = c1 - c0
        val result = Matrix(sr, sc)
        for (i in 0 until sr) {
            for (j in 0 until sc) {
                result[i, j] = this[r0 + i, c0 + j]
            }
        }
        return result
    }

    /**
     * Copies the values of [src] into this matrix starting at position
     * ([r0], [c0]).
     */
    fun setSubMatrix(r0: Int, c0: Int, src: Matrix) {
        for (i in 0 until src.rows) {
            for (j in 0 until src.cols) {
                this[r0 + i, c0 + j] = src[i, j]
            }
        }
    }

    /** Returns the trace (sum of diagonal elements). Requires a square matrix. */
    fun trace(): Double {
        require(rows == cols) { "Trace requires square matrix" }
        var sum = 0.0
        for (i in 0 until rows) sum += this[i, i]
        return sum
    }

    override fun toString(): String = buildString {
        for (i in 0 until rows) {
            append("[ ")
            for (j in 0 until cols) {
                if (j > 0) append(", ")
                append(String.format("%.6f", this@Matrix[i, j]))
            }
            appendLine(" ]")
        }
    }

    companion object {
        /** Creates an n×n identity matrix. */
        fun identity(n: Int): Matrix {
            val m = Matrix(n, n)
            for (i in 0 until n) m[i, i] = 1.0
            return m
        }

        /** Creates an n×n zero matrix. */
        fun zeros(rows: Int, cols: Int): Matrix = Matrix(rows, cols)

        /**
         * Creates the 3×3 skew-symmetric (cross-product) matrix of a 3-vector.
         *
         *     [v]× = |  0  -v₂  v₁ |
         *            |  v₂  0  -v₀ |
         *            | -v₁  v₀  0  |
         *
         * Such that [v]× · u = v × u for any 3-vector u.
         */
        fun skewSymmetric(v: DoubleArray): Matrix {
            require(v.size == 3) { "Skew-symmetric requires 3-vector" }
            return Matrix(3, 3, doubleArrayOf(
                0.0,   -v[2],  v[1],
                v[2],   0.0,  -v[0],
                -v[1],  v[0],  0.0,
            ))
        }

        /** Creates a diagonal matrix from a vector of diagonal elements. */
        fun diagonal(diag: DoubleArray): Matrix {
            val n = diag.size
            val m = Matrix(n, n)
            for (i in 0 until n) m[i, i] = diag[i]
            return m
        }

        /**
         * Creates a column vector (n×1 matrix) from a [DoubleArray].
         */
        fun columnVector(v: DoubleArray): Matrix = Matrix(v.size, 1, v.copyOf())
    }
}
