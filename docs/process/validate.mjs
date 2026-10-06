// Usage: node validate.mjs <file.bpmn>
// 1) bpmn-moddle import (schema/reference warnings), 2) bpmnlint "recommended" rules.
import { readFile } from 'node:fs/promises';
import { BpmnModdle } from 'bpmn-moddle';
import { Linter } from 'bpmnlint';
import NodeResolver from 'bpmnlint/lib/resolver/node-resolver.js';

const file = process.argv[2];
const xml = await readFile(file, 'utf8');
const moddle = new BpmnModdle();
const { rootElement, warnings } = await moddle.fromXML(xml, 'bpmn:Definitions');
console.log(`moddle: ${warnings.length} warning(s)`);
for (const w of warnings) console.log('  -', w.message);

const linter = new Linter({ config: { extends: 'bpmnlint:recommended' }, resolver: new NodeResolver() });
const reports = await linter.lint(rootElement);
let n = 0;
for (const [rule, items] of Object.entries(reports)) {
  for (const it of items) { n++; console.log(`  [${it.category}] ${rule}: ${it.id} – ${it.message}`); }
}
console.log(`bpmnlint: ${n} finding(s)`);
process.exit(warnings.length + n > 0 ? 1 : 0);
