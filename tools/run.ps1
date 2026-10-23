param([ValidateSet('test','firmware','coremark','coremark-test','ip','pds')][string]$Task='test',
 [int]$Iterations=5000,
 [string]$Python='', [string]$PdsHome='',
 [ValidateSet('active','baseline','o3','o3_inline80')][string]$CompilerProfile='active')
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
if(!$Python) {
 $candidate=Get-Command python -ErrorAction SilentlyContinue
 if($candidate){$Python=$candidate.Source}
 else {$Python=Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'}
}
Push-Location $projectRoot
try {
 switch($Task) {
  'test' {
   & $Python tools/check_stage_opt.py
   if($LASTEXITCODE -ne 0){throw 'Memory turnover tests failed'}
   & $Python tools/check_pairing_model.py
   if($LASTEXITCODE -ne 0){throw 'Pairing assessment model checks failed'}
   & $Python tools/check_multiply.py
   if($LASTEXITCODE -ne 0){throw 'Multiply pipeline tests failed'}
   & $Python tools/check_prediction.py
   if($LASTEXITCODE -ne 0){throw 'Predictor recovery tests failed'}
   & $Python tools/check_fetch_equivalence.py
   if($LASTEXITCODE -ne 0){throw 'Fetch equivalence failed'}
   & $Python tools/check_execute_equivalence.py
   if($LASTEXITCODE -ne 0){throw 'Execute equivalence failed'}
   & $Python simulation/scripts/run/regression.py
   if($LASTEXITCODE -ne 0){throw 'Core regression failed'}
   & $Python simulation/scripts/run/isa.py
   if($LASTEXITCODE -ne 0){throw 'ISA fixtures failed'}
  }
  'firmware' {& $Python tools/build_firmware.py;if($LASTEXITCODE -ne 0){throw 'Firmware build failed'}}
  'coremark' {
   $profileName=$CompilerProfile
   $buildArgs=@('--iterations',$Iterations,'--install')
   if ($profileName -eq 'active') {
    if (Test-Path 'docs/active_compiler_profile.json') {
     $profileRecord=Get-Content 'docs/active_compiler_profile.json' -Raw | ConvertFrom-Json
     if ($profileRecord.compatible_rtl_manifest_sha256 -ne (Get-FileHash 'docs/active_optimization_baseline.json' -Algorithm SHA256).Hash) { throw 'Compiler profile needs revalidation for current RTL' }
     $profileName=$profileRecord.profile
     $buildArgs+=@('--source-date-epoch',$profileRecord.source_date_epoch,'--cpu-hz',$profileRecord.hardware.configured_cpu_hz)
    } else { $profileName='baseline' }
   }
   $buildArgs+=@('--profile',$profileName)
   if ($profileName -ne 'baseline') { $buildArgs+=@('--tag',('active_'+$profileName)) }
   & $Python tools/build_coremark.py @buildArgs
   if($LASTEXITCODE -ne 0){throw 'CoreMark build failed'}
  }
  'coremark-test' {& $Python simulation/scripts/run/coremark.py --iterations $Iterations;if($LASTEXITCODE -ne 0){throw 'CoreMark simulation failed'}}
  'ip' {
   if(!$PdsHome){$PdsHome=& $Python -c "import sys;sys.path.insert(0,'tools');from build_main import find_pds;print(find_pds().parent.parent)"}
   & $Python tools/prepare_pango.py --pds $PdsHome
   if($LASTEXITCODE -ne 0){throw 'IP generation failed'}
  }
  'pds' {
   if(Test-Path 'hardware/pds/main_manifest.json') {
    $mainArgs=@()
    if($PdsHome){$mainArgs+=@('--pds-home',$PdsHome)}
    & $Python -X utf8 tools/build_main.py @mainArgs
    if($LASTEXITCODE -ne 0){throw 'Main project build or bitstream verification failed'}
    break
   }
   if(Test-Path 'docs/active_optimization_baseline.json') {
    & $Python -X utf8 tools/build_optimized.py --pds-home $PdsHome
    if($LASTEXITCODE -ne 0){throw 'Active optimization build failed'}
    break
   }
   if(Test-Path 'docs/board5000_20261022/board_manifest.json') {
    & $Python -X utf8 tools/build_board5000.py --pds-home $PdsHome
    if($LASTEXITCODE -ne 0){throw 'Board5000 native build failed'}
    break
   }
   Set-Location hardware/pds
   & (Join-Path $PdsHome 'bin/pds_shell.exe') -f new_core.tcl
   if($LASTEXITCODE -ne 0){throw 'PDS failed; also inspect its report for stage errors'}
  }
 }
} finally {Pop-Location}
