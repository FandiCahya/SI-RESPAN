

def user_roles(request):
    """
    Fungsi ini akan menambahkan variabel 'is_admin' ke semua template.
    """
    is_admin = False
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.groups.filter(name='admin_data').exists():
            is_admin = True
    return {'is_admin': is_admin}