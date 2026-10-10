param([string]$DataFolder = (Join-Path (Split-Path $PSScriptRoot -Parent) 'data'))
# Run with this PBIP project closed in Desktop.
$ErrorActionPreference = 'Stop'
$resolvedData = (Resolve-Path -LiteralPath $DataFolder).Path.TrimEnd('\')
foreach ($name in @('secom.data','secom_labels.data')) {
    if (-not (Test-Path -LiteralPath (Join-Path $resolvedData $name) -PathType Leaf)) {throw "Missing source file: $name"}
}
$expressionFile = Join-Path (Split-Path $PSScriptRoot -Parent) 'powerbi\SemiconductorQuality.SemanticModel\definition\expressions.tmdl'
$source = [IO.File]::ReadAllText($expressionFile)
$pattern = '(?m)^expression ''Data Folder'' = "(?:[^"]|"")*"(?= meta)'
if ([regex]::Matches($source,$pattern).Count -ne 1) {throw 'Expected exactly one Data Folder parameter.'}
$replacement = 'expression ''Data Folder'' = "' + $resolvedData.Replace('"','""') + '"'
$source = [regex]::Replace($source,$pattern,[System.Text.RegularExpressions.MatchEvaluator]{param($match) $replacement})
[IO.File]::WriteAllText($expressionFile,$source,[Text.UTF8Encoding]::new($false))
Write-Output "Data Folder configured: $resolvedData"
Write-Output 'Open powerbi\SemiconductorQuality.pbip and select Home > Refresh.'
