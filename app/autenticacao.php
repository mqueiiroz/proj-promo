<?php
declare(strict_types=1);

const HASH_LOGIN_INEXISTENTE = '$argon2id$v=19$m=65536,t=4,p=1$ZWU1R2o5VFN3VGpoUmpqaQ$sqbx5LPeKspj+3kXBmZYFWRHTytSgrxwkeVxviKTOSg';

function iniciarSessaoPainel(): void
{
    ini_set('session.use_strict_mode', '1');
    ini_set('session.use_only_cookies', '1');
    session_name('promo_painel');
    session_set_cookie_params([
        'lifetime' => 0,
        'path' => '/',
        'secure' => getenv('RENDER') === 'true' || in_array($_SERVER['HTTPS'] ?? '', ['on', '1'], true),
        'httponly' => true,
        'samesite' => 'Strict',
    ]);
    if (!session_start()) {
        throw new RuntimeException('Sessão indisponível.');
    }
    if (isset($_SESSION['usuario_id']) && ($_SESSION['ultima_atividade'] ?? 0) < time() - 1800) {
        $_SESSION = [];
        if (!session_regenerate_id(true)) {
            throw new RuntimeException('Sessão indisponível.');
        }
    }
}

function tokenPainel(): string
{
    return $_SESSION['csrf'] ??= bin2hex(random_bytes(32));
}

function tokenPainelValido(): bool
{
    $enviado = $_POST['csrf'] ?? null;
    return is_string($enviado) && isset($_SESSION['csrf']) && hash_equals($_SESSION['csrf'], $enviado);
}

function emailPainelValido(string $email): bool
{
    return strlen($email) <= 200 && filter_var($email, FILTER_VALIDATE_EMAIL) !== false;
}

function registrarTentativaPainel(): bool
{
    $pasta = dirname(__DIR__) . '/logs';
    if (!is_dir($pasta) && !@mkdir($pasta, 0700) && !is_dir($pasta)) {
        throw new RuntimeException('Controle de tentativas indisponível.');
    }
    $arquivo = @fopen($pasta . '/tentativas-painel.json', 'c+');
    if ($arquivo === false) {
        throw new RuntimeException('Controle de tentativas indisponível.');
    }
    try {
        if (!flock($arquivo, LOCK_EX)) {
            throw new RuntimeException('Controle de tentativas indisponível.');
        }
        $conteudo = stream_get_contents($arquivo);
        $registros = $conteudo === '' ? [] : json_decode($conteudo, true, 512, JSON_THROW_ON_ERROR);
        $agora = time();
        $registros = array_filter($registros, static fn(array $registro): bool => $registro['expira'] > $agora);
        // Usa o endereço da conexão direta, sem confiar em cabeçalhos enviados pelo cliente.
        $origem = hash('sha256', $_SERVER['REMOTE_ADDR'] ?? '');
        $registro = $registros[$origem] ?? ['expira' => $agora + 300, 'total' => 0];
        if ($registro['total'] >= 10) {
            return false;
        }
        $registro['total']++;
        $registros[$origem] = $registro;
        $json = json_encode($registros, JSON_THROW_ON_ERROR);
        if (!rewind($arquivo) || fwrite($arquivo, $json) !== strlen($json)
            || !ftruncate($arquivo, strlen($json)) || !fflush($arquivo)) {
            throw new RuntimeException('Controle de tentativas indisponível.');
        }
        return true;
    } finally {
        fclose($arquivo);
    }
}

function autenticarPainel(string $email, string $senha): ?string
{
    $usuario = false;
    if (emailPainelValido($email)) {
        $consulta = conectarBanco()->prepare('SELECT ID, SENHA_HASH FROM USUARIO WHERE EMAIL = :email');
        $consulta->execute(['email' => $email]);
        $usuario = $consulta->fetch();
    }
    $hash = $usuario === false ? HASH_LOGIN_INEXISTENTE : $usuario['SENHA_HASH'];
    $limite = str_starts_with($hash, '$2') ? 72 : 1024;
    $senhaValida = strlen($senha) <= $limite && !str_contains($senha, "\0") && password_verify($senha, $hash);
    return $senhaValida && $usuario !== false ? (string) $usuario['ID'] : null;
}
