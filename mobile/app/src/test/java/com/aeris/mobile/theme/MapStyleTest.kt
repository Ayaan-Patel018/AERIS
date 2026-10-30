package com.aeris.mobile.theme

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class MapStyleTest {

    private fun loadStyleContent(theme: String): String {
        val file = File("src/main/assets/styles/aeris-$theme.json")
        assertTrue("Style file should exist: ${file.absolutePath}", file.exists())
        return file.readText()
    }

    @Test
    fun testNightStyleLayers() {
        val content = loadStyleContent("night")
        assertTrue(content.contains("\"name\": \"AERIS Night\""))
        assertTrue(content.contains("\"version\": 8"))

        val requiredLayers = listOf(
            "\"id\": \"background\"",
            "\"id\": \"landuse_park\"",
            "\"id\": \"water\"",
            "\"id\": \"waterway\"",
            "\"id\": \"building\"",
            "\"id\": \"railway\"",
            "\"id\": \"road_casing\"",
            "\"id\": \"road_minor_fill\"",
            "\"id\": \"road_secondary_fill\"",
            "\"id\": \"road_primary_fill\"",
            "\"id\": \"road_motorway_fill\"",
            "\"id\": \"boundary\"",
            "\"id\": \"road_name\"",
            "\"id\": \"place_label\""
        )

        for (layer in requiredLayers) {
            assertTrue("Night style should contain $layer", content.contains(layer))
        }
    }

    @Test
    fun testDayStyleLayers() {
        val content = loadStyleContent("day")
        assertTrue(content.contains("\"name\": \"AERIS Day\""))
        assertTrue(content.contains("\"version\": 8"))

        val requiredLayers = listOf(
            "\"id\": \"background\"",
            "\"id\": \"landuse_park\"",
            "\"id\": \"water\"",
            "\"id\": \"road_casing\"",
            "\"id\": \"road_primary_fill\""
        )

        for (layer in requiredLayers) {
            assertTrue("Day style should contain $layer", content.contains(layer))
        }
    }

    @Test
    fun testContrastRequirements() {
        // R2 § 2: Cobalt, AmberLine, and Teal contrast compliance against backgrounds
        fun lum(r: Int, g: Int, b: Int): Double {
            fun c(v: Int): Double {
                val s = v / 255.0
                return if (s <= 0.03928) s / 12.92 else Math.pow((s + 0.055) / 1.055, 2.4)
            }
            return 0.2126 * c(r) + 0.7152 * c(g) + 0.0722 * c(b)
        }

        fun contrast(hex1: String, hex2: String): Double {
            fun parse(hex: String) = Triple(
                hex.substring(1, 3).toInt(16),
                hex.substring(3, 5).toInt(16),
                hex.substring(5, 7).toInt(16)
            )
            val l1 = lum(parse(hex1).first, parse(hex1).second, parse(hex1).third)
            val l2 = lum(parse(hex2).first, parse(hex2).second, parse(hex2).third)
            val max = maxOf(l1, l2)
            val min = minOf(l1, l2)
            return (max + 0.05) / (min + 0.05)
        }

        // Night Land: #0F1A24, Night Cobalt: #6D8BFF, Night Amber: #F2A93B
        val nightCobalt = contrast("#6D8BFF", "#0F1A24")
        assertTrue("Night cobalt contrast should be >= 3.0: $nightCobalt", nightCobalt >= 3.0)

        val nightAmber = contrast("#F2A93B", "#0F1A24")
        assertTrue("Night amber contrast should be >= 3.0: $nightAmber", nightAmber >= 3.0)

        // Day White Casing: #FFFFFF, Day AmberLine: #B26A00
        val dayAmberLine = contrast("#B26A00", "#FFFFFF")
        assertTrue("Day amberLine contrast against white must be >= 3.0: $dayAmberLine", dayAmberLine >= 3.0)
    }
}
