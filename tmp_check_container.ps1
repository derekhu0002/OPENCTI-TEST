Set-Location $PSScriptRoot

$build = docker-compose build mirror-sync 2>&1 | Out-String
$build | Set-Content -Path .\tmp_container_build.txt -Encoding utf8

docker-compose up -d mirror-sync *> .\tmp_container_up.txt

docker-compose ps mirror-sync 2>&1 | Out-String | Set-Content -Path .\tmp_container_ps.txt -Encoding utf8

docker-compose exec -T mirror-sync python -c "from pathlib import Path; text=Path('/app/mirror-sync/service.py').read_text(encoding='utf-8'); print('HAS_LOOKBACK', 'RECENT_LOOKBACK_MINUTES' in text); start=text.find('def _effective_since'); print(text[start:start+500])" 2>&1 | Out-String | Set-Content -Path .\tmp_container_code.txt -Encoding utf8
