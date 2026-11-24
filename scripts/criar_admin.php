<?php
declare(strict_types=1);

require dirname(__DIR__) . '/app/banco.php';
require dirname(__DIR__) . '/app/autenticacao.php';

$email = strtolower(trim($argv[1] ?? ''));
$entrada = fgets(STDIN, 1027);
$senha = $entrada === false ? '' : rtrim($entrada, "\r\n");
if (!emailPainelValido($email) || strlen($senha) > 1024 || str_contains($senha, "\0")
    || preg_match('/\A.{8,}\z/us', $senha) !== 1) {
    fwrite(STDERR, "Informe um e-mail válido e uma senha de pelo menos 8 caracteres (até 1024 bytes).\n");
    exit(1);
}

try {
    $hash = password_hash($senha, PASSWORD_ARGON2ID);
    unset($entrada, $senha);
    $banco = conectarBanco();
    $consulta = $banco->prepare('INSERT INTO USUARIO (EMAIL, SENHA_HASH) VALUES (:email, :hash)');
    $consulta->execute(['email' => $email, 'hash' => $hash]);
    fwrite(STDOUT, "Administrador cadastrado.\n");
} catch (Throwable $erro) {
    fwrite(STDERR, "Não foi possível cadastrar o administrador. Verifique a conexão e se o e-mail já está cadastrado.\n");
    exit(1);
}
