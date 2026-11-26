<?php
declare(strict_types=1);

require __DIR__ . '/banco.php';
require __DIR__ . '/autenticacao.php';
require __DIR__ . '/layout.php';
require __DIR__ . '/produto-url.php';

ini_set('display_errors', '0');
header('Content-Type: text/html; charset=UTF-8');
header('Cache-Control: no-store');
header("Content-Security-Policy: default-src 'none'; style-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'");

$metodo = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$permitidos = match ($caminho) {
    '/login' => ['GET', 'POST'],
    '/logout' => ['POST'],
    default => ['GET'],
};
if (!in_array($metodo, $permitidos, true)) {
    http_response_code(405);
    header('Allow: ' . implode(', ', $permitidos));
    return;
}

$mensagem = '';
try {
    iniciarSessaoPainel();
    if ($metodo === 'POST' && !tokenPainelValido()) {
        http_response_code(403);
        $mensagem = 'Sessão do formulário expirada. Recarregue a página e tente novamente.';
    } elseif ($caminho === '/logout') {
        $_SESSION = [];
        $cookie = session_get_cookie_params();
        setcookie(session_name(), '', [
            'expires' => time() - 3600, 'path' => $cookie['path'],
            'secure' => $cookie['secure'], 'httponly' => true, 'samesite' => 'Strict',
        ]);
        session_destroy();
        header('Location: /login', true, 303);
        return;
    } elseif ($caminho === '/painel' && !isset($_SESSION['usuario_id'])) {
        header('Location: /login', true, 303);
        return;
    } elseif ($caminho === '/login') {
        if (!isset($_SESSION['usuario_id']) && $metodo === 'POST') {
            if (!registrarTentativaPainel()) {
                http_response_code(429);
                header('Retry-After: 300');
                $mensagem = 'Muitas tentativas. Aguarde alguns minutos e tente novamente.';
            } else {
                $email = $_POST['email'] ?? '';
                $senha = $_POST['senha'] ?? '';
                $usuario = autenticarPainel(is_string($email) ? strtolower(trim($email)) : '', is_string($senha) ? $senha : '');
                if ($usuario !== null) {
                    if (!session_regenerate_id(true)) {
                        throw new RuntimeException('Sessão indisponível.');
                    }
                    $_SESSION = ['usuario_id' => $usuario, 'ultima_atividade' => time()];
                } else {
                    http_response_code(401);
                    $mensagem = 'E-mail ou senha inválidos.';
                }
            }
        }
        if (isset($_SESSION['usuario_id'])) {
            header('Location: /painel', true, 303);
            return;
        }
    }
    $autenticado = isset($_SESSION['usuario_id']);
    if ($autenticado) {
        $_SESSION['ultima_atividade'] = time();
    }
    $csrf = tokenPainel();
} catch (Throwable $erro) {
    http_response_code(503);
    echo 'O painel está temporariamente indisponível.';
    return;
}
$mostrarPainel = $autenticado && $caminho === '/painel';
$mostrarProdutos = $mostrarPainel && ($_GET['secao'] ?? '') === 'produtos';
session_write_close();
$monitoramento = null;
$catalogo = null;
if ($mostrarPainel) {
    require __DIR__ . '/monitoramento.php';
    $falhaLocal = lerFalhaLocalColeta();
    $paginaEventos = filter_input(INPUT_GET, 'eventos', FILTER_VALIDATE_INT, [
        'options' => ['min_range' => 1, 'max_range' => intdiv(PHP_INT_MAX, 20)],
    ]) ?: 1;
    try {
        $banco = conectarBanco();
        if ($mostrarProdutos) {
            $catalogo = consultarCatalogoPainel($banco);
        } else {
            $monitoramento = consultarMonitoramento($banco, $paginaEventos);
        }
    } catch (Throwable $erro) {
        http_response_code(503);
    }
}
abrirPagina($autenticado ? 'Painel administrativo' : 'Entrar', $caminho, [], $autenticado);
?>
    <?php if ($mensagem !== ''): ?>
        <p role="alert"><?= htmlspecialchars($mensagem, ENT_QUOTES, 'UTF-8') ?></p>
    <?php endif; ?>
    <?php if ($autenticado): ?>
        <div class="painel-topo">
            <div>
                <h1><?= $mostrarProdutos ? 'Produtos' : 'Gestão de ofertas' ?></h1>
                <?php if (!$mostrarProdutos): ?><p>Acompanhe as consultas ao feed e a última importação de cada produto.</p><?php endif; ?>
            </div>
            <form action="/logout" method="post">
                <input type="hidden" name="csrf" value="<?= $csrf ?>">
                <button class="home-botao" type="submit">Sair</button>
            </form>
        </div>
        <?php if ($mostrarPainel): ?>
            <nav class="painel-secoes" aria-label="Seções do painel">
                <a class="acao-secundaria" href="/painel"<?= !$mostrarProdutos ? ' aria-current="page"' : '' ?>>Gestão de ofertas</a>
                <a class="acao-secundaria" href="/painel?secao=produtos"<?= $mostrarProdutos ? ' aria-current="page"' : '' ?>>Produtos</a>
            </nav>
            <?php require __DIR__ . ($mostrarProdutos ? '/produtos-painel.php' : '/monitoramento-painel.php'); ?>
        <?php endif; ?>
    <?php else: ?>
        <section class="cartao-conta">
        <h1>Entrar</h1>
        <form class="formulario-painel" action="/login" method="post">
            <input type="hidden" name="csrf" value="<?= $csrf ?>">
            <label for="email">E-mail</label>
            <input id="email" name="email" type="email" autocomplete="username" maxlength="200" required>
            <label for="senha">Senha</label>
            <input id="senha" name="senha" type="password" autocomplete="current-password" maxlength="1024" required>
            <button class="home-botao" type="submit">Entrar</button>
        </form>
        <nav class="conta-links" aria-label="Opções da conta">
            <a class="acao-secundaria" href="/criar-conta">Criar conta</a>
            <a class="acao-secundaria" href="/recuperar-senha">Esqueci minha senha</a>
        </nav>
        </section>
    <?php endif; ?>
<?php fecharPagina(); ?>
