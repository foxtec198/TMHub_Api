# Teste simples para verificar se o auth.py está funcionando
import sys
sys.path.insert(0, '/home/guibs/api_tmhub')

try:
    from services.auth import AuthService
    print("AuthService importado com sucesso")
    
    # Testar a função issue_user_token
    class MockUser:
        id = 1
        role = "USER"
        token_version = 0
        token_sem_expiracao = False
    
    user = MockUser()
    result = AuthService.issue_user_token(user)
    print(f"issue_user_token funcionando: {result[:50]}...")
    print("SUCESSO!")
except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()
