from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.http import HttpResponse

from .forms import RegisterForm

User = get_user_model()

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Salva o usuário no banco, mas ainda não loga
            user = form.save(commit=False)
            user.is_active = True
            user.email_verified = False # Nasce não verificado, conforme combinamos
            user.save()

            # Gera um Token seguro e o ID codificado na URL
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            # Constrói o link absoluto
            domain = request.get_host()
            link = f"http://{domain}{reverse('verify_email', kwargs={'uidb64': uid, 'token': token})}"

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