#!/usr/bin/env node
import {spawn} from 'node:child_process';
const child=spawn(process.env.UNIVERSAL_SATELLITE_PYTHON||'python',['-m','universal_satellite',...process.argv.slice(2)],{stdio:'inherit'});
child.on('error',()=>{console.error('Install the Python core or set UNIVERSAL_SATELLITE_PYTHON.');process.exitCode=1;});
child.on('exit',(code,signal)=>{process.exitCode=code??1;});
