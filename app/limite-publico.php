<?php
declare(strict_types=1);

function ipVisitante(): string
{
    // O tráfego público da Render passa pelo Cloudflare. A aplicação não recebe
    // chamadas de outros serviços pela rede privada da Render.
    $ip = $_SERVER['REMOTE_ADDR'] ?? '';
    if (getenv('RENDER') === 'true') {
        $encaminhado = $_SERVER['HTTP_CF_CONNECTING_IP'] ?? '';
        if (filter_var($encaminhado, FILTER_VALIDATE_IP) !== false) {
            $ip = $encaminhado;
        }
    }
    $binario = @inet_pton($ip);
    if ($binario !== false && str_starts_with($binario, str_repeat("\0", 10) . "\xff\xff")) {
        $binario = substr($binario, 12);
    }
    return $binario === false ? '' : $binario;
}

function registrarRequisicaoPublica(string $grupo, int $limite): int
{
    $chave = hash('sha256', ipVisitante());
    $pasta = dirname(__DIR__) . '/logs';
    if (!is_dir($pasta) && !@mkdir($pasta, 0700) && !is_dir($pasta)) {
        throw new RuntimeException('Pasta de contadores indisponível.');
    }

    $particao = substr($chave, 0, 2);
    $arquivo = @fopen("{$pasta}/limite-publico-{$grupo}-{$particao}.json", 'c+');
    if ($arquivo === false) {
        throw new RuntimeException('Contador indisponível.');
    }
    try {
        if (!flock($arquivo, LOCK_EX)) {
            throw new RuntimeException('Bloqueio do contador indisponível.');
        }
        $conteudo = stream_get_contents($arquivo);
        if ($conteudo === false) {
            throw new RuntimeException('Não foi possível ler o contador.');
        }
        $registros = $conteudo === '' ? [] : json_decode($conteudo, true);
        if (!is_array($registros)) {
            error_log('Contador de requisições públicas reiniciado após leitura inválida.');
            $registros = [];
        }
        $agora = time();
        $registros = array_filter($registros, static fn (array $registro): bool => $registro['expira'] > $agora);
        $registro = $registros[$chave] ?? ['expira' => $agora + 60, 'total' => 0];
        if ($registro['total'] >= $limite) {
            return $registro['expira'] - $agora;
        }
        $registro['total']++;
        $registros[$chave] = $registro;
        $json = json_encode($registros, JSON_THROW_ON_ERROR);
        if (!rewind($arquivo) || fwrite($arquivo, $json) !== strlen($json)
            || !ftruncate($arquivo, strlen($json)) || !fflush($arquivo)) {
            throw new RuntimeException('Não foi possível gravar o contador.');
        }
        return 0;
    } finally {
        fclose($arquivo);
    }
}

function limitarRequisicoesPublicas(string $grupo, int $limite): bool
{
    try {
        $espera = registrarRequisicaoPublica($grupo, $limite);
    } catch (Throwable) {
        error_log('Não foi possível aplicar o limite de requisições públicas.');
        return true;
    }
    if ($espera === 0) {
        return true;
    }
    http_response_code(429);
    header('Retry-After: ' . $espera);
    header('Cache-Control: no-store');
    $mensagem = 'Muitas requisições. Aguarde um momento e tente novamente.';
    if ($grupo === 'api') {
        echo json_encode(['erro' => $mensagem], JSON_UNESCAPED_UNICODE);
    } else {
        header('Content-Type: text/plain; charset=UTF-8');
        echo $mensagem;
    }
    return false;
}
