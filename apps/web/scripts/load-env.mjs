import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const configFiles = ['app.env', 'services.env'];

function parseEnvFile(filePath) {
    const values = {};
    for (const rawLine of fs.readFileSync(filePath, 'utf8').split(/\r?\n/)) {
        const line = rawLine.trim();
        if (!line) continue;
        const separator = line.indexOf('=');
        if (separator <= 0) throw new Error(`Linha inválida em ${filePath}: ${rawLine}`);
        const key = line.slice(0, separator).trim();
        let value = line.slice(separator + 1).trim();
        if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
            value = value.slice(1, -1);
        }
        values[key] = value;
    }
    return values;
}

export function loadConfigEnv() {
    const webRoot = fileURLToPath(new URL('..', import.meta.url));
    const directory = path.join(webRoot, 'config', 'runtime');
    const values = {};
    const origins = {};
    for (const name of configFiles) {
        const filePath = path.join(directory, name);
        if (!fs.existsSync(filePath)) throw new Error(`Arquivo de configuração ausente: ${filePath}`);
        for (const [key, value] of Object.entries(parseEnvFile(filePath))) {
            if (Object.hasOwn(values, key)) throw new Error(`Variável duplicada ${key} em ${origins[key]} e ${filePath}.`);
            values[key] = value;
            origins[key] = filePath;
        }
    }
    return values;
}
