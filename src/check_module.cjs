// Dynamic import ES module from CommonJS
const { createRequire } = module;
const require = createRequire(import.meta.url);

const layout = require('./tools/data-layout.js');
console.log('data-layout exports:', Object.keys(layout));