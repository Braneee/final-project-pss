from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('student', 'Siswa'), ('instructor', 'Instruktur'), ('admin', 'Admin')], default='student', max_length=20, verbose_name='Peran')),
                ('bio', models.TextField(blank=True, default='', verbose_name='Bio')),
                ('avatar', models.ImageField(blank=True, null=True, upload_to='avatars/', verbose_name='Avatar')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to='auth.user', verbose_name='Pengguna')),
            ],
            options={
                'verbose_name': 'Profil Pengguna',
                'verbose_name_plural': 'Profil Pengguna',
            },
        ),
    ]
