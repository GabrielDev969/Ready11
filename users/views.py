from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode, url_has_allowed_host_and_scheme
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.http import HttpResponse
from .forms import RegisterForm, LoginForm
from django.contrib import messages
from tenants.utils import effective_workspace, workspace_home_url

User = get_user_model()


def _redirect_authenticated_home(request):
    """
    Send an authenticated user to their workspace home (Início), or to the public
    landing if they don't belong to any workspace yet.
    """
    workspace = effective_workspace(request.user)
    if workspace:
        url = workspace_home_url(request, workspace)
        if url:
            return redirect(url)
    return redirect('landing')

def register_view(request):
    # Já está logado? Não faz sentido ver o cadastro.
    if request.user.is_authenticated:
        return _redirect_authenticated_home(request)

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Salva o usuário no banco, mas ainda não loga
            user = form.save(commit=False)

            user.set_password(form.cleaned_data['password'])

            user.is_active = True
            user.email_verified = False # Nasce não verificado, conforme combinamos
            user.save()

            # Gera um Token seguro e o ID codificado na URL
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            # Constrói o link absoluto (respeita http/https automaticamente)
            link = request.build_absolute_uri(
                reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
            )

            # Monta e envia o e-mail (aparecerá no seu terminal)
            assunto = 'Verifique seu E-mail para acessar o Workspace'
            mensagem = f'Olá {user.first_name},\n\nClique no link abaixo para verificar sua conta:\n\n{link}'
            
            send_mail(
                assunto,
                mensagem,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            # Redireciona para uma tela de aviso "Vá checar seu e-mail"
            return render(request, 'users/register_success.html')
    else:
        form = RegisterForm()

    return render(request, 'users/register.html', {'form': form})


def verify_email_view(request, uidb64, token):
    """ Rota que o usuário acessa ao clicar no link do e-mail """
    try:
        # Decodifica o ID e busca o usuário
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Checa se o usuário existe e se o token é válido e não expirou
    if user is not None and default_token_generator.check_token(user, token):
        user.email_verified = True
        user.save()
        # Aqui no futuro enviaremos para a tela de Login com um alerta de sucesso
        return HttpResponse("<h1>E-mail verificado com sucesso!</h1><p>Você já pode fazer login.</p>")
    else:
        return HttpResponse("<h1>Link inválido ou expirado.</h1>", status=400)

def login_view(request):
    # Já está logado? Manda direto para o workspace em vez de mostrar o login.
    if request.user.is_authenticated:
        return _redirect_authenticated_home(request)

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            
            # O Django tenta achar o usuário e validar a senha
            user = authenticate(request, username=email, password=password)

            if user is not None:
                # A nossa regra de ouro: O e-mail foi verificado?
                if not getattr(user, 'email_verified', False):
                    messages.error(request, "Por favor, verifique seu e-mail antes de acessar o sistema.")
                    return render(request, 'users/login.html', {'form': form})
                
                # Regra nativa: O super admin desativou essa conta?
                if not user.is_active:
                    messages.error(request, "Sua conta foi desativada pelo administrador.")
                    return render(request, 'users/login.html', {'form': form})

                # Tudo certo! Cria a sessão do usuário
                login(request, user)

                # Respeita o ?next= (ex.: voltar para aceitar um convite), validado
                # para impedir open redirect para hosts/esquemas não confiáveis.
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url and url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)

                # Roteamento inteligente: leva ao Início do workspace do usuário
                # (com fallback seguro se o workspace padrão não existir mais).
                return _redirect_authenticated_home(request)
            else:
                messages.error(request, "E-mail ou senha incorretos.")
    else:
        form = LoginForm()

    return render(request, 'users/login.html', {'form': form})

def logout_view(request):
    """Log the user out and return to the public landing page."""
    logout(request)
    return redirect('landing')


# Uma view provisória apenas para termos onde cair após o login
def dashboard_placeholder(request):
    return HttpResponse("<h1>Bem-vindo ao Workspace!</h1><p>Você está logado com sucesso.</p>")