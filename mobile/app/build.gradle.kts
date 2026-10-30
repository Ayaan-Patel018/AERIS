import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

// Read the Mapbox public access token from local.properties.
val localProperties = Properties().apply {
    val file = rootProject.file("local.properties")
    if (file.exists()) load(file.inputStream())
}

val mapboxToken = localProperties.getProperty("MAPBOX_ACCESS_TOKEN")
    ?: localProperties.getProperty("MAPBOX_PUBLIC_TOKEN")
    ?: System.getenv("MAPBOX_ACCESS_TOKEN")
    ?: ""

android {
    namespace = "com.aeris.mobile"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.aeris.mobile"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        // Expose the Mapbox public token to Kotlin code via BuildConfig.
        buildConfigField(
            "String",
            "MAPBOX_PUBLIC_TOKEN",
            "\"$mapboxToken\""
        )
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }

    kotlinOptions {
        jvmTarget = "11"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    // --- Core / AndroidX ---
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.lifecycle.service)
    implementation(libs.androidx.activity.compose)

    // --- Compose ---
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.compose.foundation)
    implementation(libs.androidx.navigation.compose)

    // --- Coroutines ---
    implementation(libs.kotlinx.coroutines.core)
    implementation(libs.kotlinx.coroutines.android)

    // --- Google Play Services Location ---
    implementation(libs.play.services.location)

    // --- Mapbox Maps ---
    implementation(libs.mapbox.maps)
    implementation(libs.mapbox.maps.compose)

    // --- Coil (image loading + SVG) ---
    implementation(libs.coil.compose)
    implementation(libs.coil.svg)

    // --- Test ---
    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.ui.test.junit4)
    debugImplementation(libs.androidx.ui.tooling)
    debugImplementation(libs.androidx.ui.test.manifest)
}

// Security verification task per V0 § 3
tasks.register("verifyNoCommittedSecrets") {
    description = "Fails the build if a public Mapbox token pk.eyJ is found in source files per V0 § 3"
    doLast {
        val srcDir = project.file("src")
        val forbidden = "pk." + "eyJ"
        srcDir.walkTopDown().filter { it.isFile && (it.extension == "kt" || it.extension == "xml" || it.extension == "json") }.forEach { f ->
            if (f.readText().contains(forbidden)) {
                throw GradleException("Security violation: Found forbidden public token string '${forbidden}' in tracked file: ${f.absolutePath}. Mapbox token must be provided via local.properties or environment variable MAPBOX_ACCESS_TOKEN.")
            }
        }
    }
}

tasks.named("preBuild") {
    dependsOn("verifyNoCommittedSecrets")
}
