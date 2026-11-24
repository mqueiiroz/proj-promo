param(
    [Parameter(Mandatory)]
    [string] $Email
)

$ErrorActionPreference = 'Stop'
$senha = Read-Host 'Senha do administrador' -AsSecureString
$confirmacao = Read-Host 'Confirme a senha' -AsSecureString
$senhaPtr = [IntPtr]::Zero
$confirmacaoPtr = [IntPtr]::Zero

try {
    $senhaPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($senha)
    $confirmacaoPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($confirmacao)
    $textoSenha = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($senhaPtr)
    $textoConfirmacao = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($confirmacaoPtr)
    if (![string]::Equals($textoSenha, $textoConfirmacao, [StringComparison]::Ordinal) -or
        $textoSenha.Contains("`r") -or $textoSenha.Contains("`n")) {
        throw 'Confirmação de senha inválida.'
    }
    $OutputEncoding = [Text.UTF8Encoding]::new($false)
    $textoSenha | & php (Join-Path $PSScriptRoot 'criar_admin.php') $Email
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    if ($senhaPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($senhaPtr)
    }
    if ($confirmacaoPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($confirmacaoPtr)
    }
    $textoSenha = $null
    $textoConfirmacao = $null
    $senha.Dispose()
    $confirmacao.Dispose()
}
