import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {flattenMessages,interpolate,validateCatalog} from '../src/lib/i18n-core.ts';
const files=Object.fromEntries(['az','en','ru'].map(l=>[l,JSON.parse(fs.readFileSync(new URL(`../src/locales/${l}.json`,import.meta.url),'utf8'))]));
const catalogs=Object.fromEntries(Object.entries(files).map(([l,d])=>[l,flattenMessages(d.messages)]));
test('AZ EN RU have identical complete keys and interpolation placeholders',()=>{for(const locale of ['en','ru'])assert.deepEqual(validateCatalog(catalogs.az,catalogs[locale]),[]);assert.ok(Object.keys(catalogs.az).length>300)});
test('locale metadata matches actual supplied/generated language',()=>{for(const l of ['az','en','ru'])assert.equal(files[l]._meta.locale,l);assert.equal(catalogs.en['support.historyTitle'],'Conversation History');assert.match(catalogs.ru['support.historyTitle'],/[А-Яа-я]/)});
test('interpolation preserves zero and treats values as literal text',()=>{assert.equal(interpolate('{count} / {amount}',{count:0,amount:'$&'}),'0 / $&');assert.equal(interpolate('{name} {unknown}',{name:'Ayla'}),'Ayla {unknown}')});
test('validation detects missing translations and renamed placeholders',()=>{assert.deepEqual(validateCatalog({'a':'{count} entries'},{a:'{total} entries'}),['a: placeholder mismatch']);assert.deepEqual(validateCatalog({a:'Hello'},{}),['a: missing translation'])});
