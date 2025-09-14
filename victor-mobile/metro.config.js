const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Add 'bin' and 'mil' to assetExts for whisper.rn
config.resolver.assetExts.push('bin', 'mil');

module.exports = config;
