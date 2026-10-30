import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PALETTE = {
  night: {
    name: 'AERIS Night',
    background: '#0F1A24',
    park: '#12302B',
    water: '#0A2533',
    roadMinor: '#223240',
    roadSecondary: '#2D4050',
    roadPrimary: '#3D566A',
    motorway: '#4A6A82',
    roadCasing: '#09111A',
    rail: '#26384A',
    building: '#13212C',
    buildingOpacity: 0.6,
    labelText: '#8CA0B0',
    majorLabelText: '#B9C8D3',
    labelHalo: '#0C1319',
    boundary: '#26384A',
  },
  day: {
    name: 'AERIS Day',
    background: '#EDF0EC',
    park: '#D5E7D8',
    water: '#C4DEEB',
    roadMinor: '#FFFFFF',
    roadSecondary: '#FFFFFF',
    roadPrimary: '#FFFFFF',
    motorway: '#FFFFFF',
    roadCasing: '#CBD4D9',
    rail: '#BFC8CE',
    building: '#E4E8E3',
    buildingOpacity: 0.7,
    labelText: '#5E6E7A',
    majorLabelText: '#33434F',
    labelHalo: '#F5F7F6',
    boundary: '#C5CDD2',
  }
};

function generateStyle(themeKey) {
  const p = PALETTE[themeKey];
  return {
    version: 8,
    name: p.name,
    metadata: {
      'aeris:theme': themeKey,
      'aeris:version': '2.0.0',
    },
    sources: {
      openmaptiles: {
        type: 'vector',
        url: 'https://tiles.openfreemap.org/planet'
      }
    },
    glyphs: 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf',
    layers: [
      // 1. Background
      {
        id: 'background',
        type: 'background',
        paint: {
          'background-color': p.background
        }
      },
      // 2. Landuse & Parks
      {
        id: 'landuse_park',
        type: 'fill',
        source: 'openmaptiles',
        'source-layer': 'landuse',
        filter: ['in', 'class', 'park', 'cemetery', 'wood', 'forest', 'grass'],
        paint: {
          'fill-color': p.park
        }
      },
      // 3. Water Polygons
      {
        id: 'water',
        type: 'fill',
        source: 'openmaptiles',
        'source-layer': 'water',
        paint: {
          'fill-color': p.water
        }
      },
      // 4. Waterways
      {
        id: 'waterway',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'waterway',
        paint: {
          'line-color': p.water,
          'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1, 16, 4]
        }
      },
      // 5. Buildings (z >= 15)
      {
        id: 'building',
        type: 'fill',
        source: 'openmaptiles',
        'source-layer': 'building',
        minzoom: 15,
        paint: {
          'fill-color': p.building,
          'fill-opacity': p.buildingOpacity
        }
      },
      // 6. Rail
      {
        id: 'railway',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'transportation',
        filter: ['==', 'class', 'rail'],
        paint: {
          'line-color': p.rail,
          'line-width': 1.5
        }
      },
      // 7. Road Casings
      {
        id: 'road_casing',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'transportation',
        filter: ['in', 'class', 'motorway', 'trunk', 'primary', 'secondary', 'tertiary'],
        minzoom: 13,
        layout: {
          'line-cap': 'round',
          'line-join': 'round'
        },
        paint: {
          'line-color': p.roadCasing,
          'line-width': ['interpolate', ['linear'], ['zoom'], 13, 3, 17, 14, 19, 24]
        }
      },
      // 8. Road Minor Fill
      {
        id: 'road_minor_fill',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'transportation',
        filter: ['in', 'class', 'minor', 'service', 'street'],
        minzoom: 13,
        layout: {
          'line-cap': 'round',
          'line-join': 'round'
        },
        paint: {
          'line-color': p.roadMinor,
          'line-width': ['interpolate', ['linear'], ['zoom'], 14, 1.5, 17, 5, 19, 10]
        }
      },
      // 9. Secondary/Tertiary Roads
      {
        id: 'road_secondary_fill',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'transportation',
        filter: ['in', 'class', 'secondary', 'tertiary'],
        layout: {
          'line-cap': 'round',
          'line-join': 'round'
        },
        paint: {
          'line-color': p.roadSecondary,
          'line-width': ['interpolate', ['linear'], ['zoom'], 10, 0.8, 14, 3, 17, 8, 19, 15]
        }
      },
      // 10. Primary/Trunk Roads
      {
        id: 'road_primary_fill',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'transportation',
        filter: ['in', 'class', 'primary', 'trunk'],
        layout: {
          'line-cap': 'round',
          'line-join': 'round'
        },
        paint: {
          'line-color': p.roadPrimary,
          'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1.2, 14, 4, 17, 10, 19, 19]
        }
      },
      // 11. Motorway Fill
      {
        id: 'road_motorway_fill',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'transportation',
        filter: ['==', 'class', 'motorway'],
        layout: {
          'line-cap': 'round',
          'line-join': 'round'
        },
        paint: {
          'line-color': p.motorway,
          'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1.5, 14, 5, 17, 12, 19, 22]
        }
      },
      // 12. Boundaries
      {
        id: 'boundary',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'boundary',
        paint: {
          'line-color': p.boundary,
          'line-dasharray': [4, 4],
          'line-width': 1.0
        }
      },
      // 13. Road Names
      {
        id: 'road_name',
        type: 'symbol',
        source: 'openmaptiles',
        'source-layer': 'transportation_name',
        minzoom: 13,
        layout: {
          'symbol-placement': 'line',
          'text-field': '{name}',
          'text-font': ['Noto Sans Regular'],
          'text-size': ['interpolate', ['linear'], ['zoom'], 13, 11, 17, 13]
        },
        paint: {
          'text-color': p.labelText,
          'text-halo-color': p.labelHalo,
          'text-halo-width': 1.5
        }
      },
      // 14. Major Place Labels
      {
        id: 'place_label',
        type: 'symbol',
        source: 'openmaptiles',
        'source-layer': 'place',
        layout: {
          'text-field': '{name}',
          'text-font': ['Noto Sans Medium'],
          'text-size': ['interpolate', ['linear'], ['zoom'], 8, 12, 14, 16]
        },
        paint: {
          'text-color': p.majorLabelText,
          'text-halo-color': p.labelHalo,
          'text-halo-width': 1.5
        }
      }
    ]
  };
}

const outDir = path.resolve(__dirname, '../mobile/app/src/main/assets/styles');
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

fs.writeFileSync(path.join(outDir, 'aeris-night.json'), JSON.stringify(generateStyle('night'), null, 2));
fs.writeFileSync(path.join(outDir, 'aeris-day.json'), JSON.stringify(generateStyle('day'), null, 2));

console.log('Successfully generated aeris-night.json and aeris-day.json in', outDir);
