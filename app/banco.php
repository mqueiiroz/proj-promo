<?php
declare(strict_types=1);

/** Lê a configuração local; variáveis do processo têm prioridade. */
function conectarBanco(): PDO
{
    $arquivo = dirname(__DIR__) . '/.env';
    $config = is_readable($arquivo) ? @parse_ini_file($arquivo, false, INI_SCANNER_RAW) : [];
    if ($config === false) {
        throw new RuntimeException('Configuração inválida.');
    }
    $driver = getenv('DB_DRIVER');
    $driver = $driver === false ? ($config['DB_DRIVER'] ?? 'oracle') : $driver;
    if (!in_array($driver, ['oracle', 'postgresql'], true)) {
        throw new RuntimeException('Driver de banco inválido.');
    }
    $campoBanco = $driver === 'postgresql' ? 'DB_NAME' : 'DB_SERVICE_NAME';
    foreach (['DB_HOST', 'DB_PORT', $campoBanco, 'DB_USER', 'DB_PASSWORD'] as $chave) {
        $ambiente = getenv($chave);
        if ($ambiente !== false) {
            $config[$chave] = $ambiente;
        }
        if (!isset($config[$chave]) || trim((string) $config[$chave]) === '') {
            throw new RuntimeException('Configuração incompleta.');
        }
    }
    if (!filter_var($config['DB_PORT'], FILTER_VALIDATE_INT, ['options' => ['min_range' => 1, 'max_range' => 65535]])
        || !preg_match('/\A[a-zA-Z0-9.-]+\z/', $config['DB_HOST'])
        || !preg_match('/\A[a-zA-Z0-9_.-]+\z/', $config[$campoBanco])) {
        throw new RuntimeException('Endereço de conexão inválido.');
    }
    $sslmode = $config['DB_HOST'] === '127.0.0.1' ? 'prefer' : 'require';
    $dsn = $driver === 'postgresql'
        ? 'pgsql:host=' . $config['DB_HOST'] . ';port=' . $config['DB_PORT']
            . ';dbname=' . $config['DB_NAME'] . ';sslmode=' . $sslmode
        : 'oci:dbname=//' . $config['DB_HOST'] . ':' . $config['DB_PORT']
            . '/' . $config['DB_SERVICE_NAME'] . ';charset=AL32UTF8';
    $banco = new PDO($dsn, $config['DB_USER'], $config['DB_PASSWORD'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_CASE => PDO::CASE_UPPER,
    ]);
    if ($driver === 'postgresql') {
        $banco->exec("SET TIME ZONE 'America/Manaus'");
    } else {
        // PDO_OCI pode retornar números como texto.
        $banco->exec("ALTER SESSION SET NLS_NUMERIC_CHARACTERS = '.,'");
    }
    return $banco;
}
