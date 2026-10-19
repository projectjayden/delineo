# Download only public simulation inputs; use Windows certificate verification.
param([string]$Output = 'data/local/source-audit/zone70.bulk')
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $Output) { throw 'Output exists; retain it or choose another path.' }
$parent = Split-Path -Parent $Output
New-Item -ItemType Directory -Force $parent | Out-Null
Add-Type -AssemblyName System.Net.Http
$client = [System.Net.Http.HttpClient]::new()
$client.Timeout = [TimeSpan]::FromSeconds(90)
$response = $client.GetAsync('https://covidmod.isi.jhu.edu/api/patterns/70?length=40320', [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
$response.EnsureSuccessStatusCode() | Out-Null
$inputStream = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
$outputStream = [System.IO.File]::Create([System.IO.Path]::GetFullPath($Output))
$buffer = New-Object byte[] 1048576
$total = 0
try {
    while (($read = $inputStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
        $total += $read
        if ($total -gt 67108864) { throw 'Download exceeded 64 MiB limit; partial file must not be used.' }
        $outputStream.Write($buffer, 0, $read)
    }
} finally {
    $outputStream.Dispose()
    $inputStream.Dispose()
    $client.Dispose()
}
Get-FileHash -LiteralPath $Output -Algorithm SHA256
Write-Output "Downloaded $total bytes. Verify hash against the study provenance before reuse."
