from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Judul')),
                ('description', models.TextField(default='', verbose_name='Deskripsi')),
                ('price', models.IntegerField(default=0, verbose_name='Harga')),
                ('level', models.CharField(choices=[('beginner', 'Pemula'), ('intermediate', 'Menengah'), ('advanced', 'Lanjutan')], default='beginner', max_length=20, verbose_name='Level')),
                ('image', models.ImageField(blank=True, null=True, upload_to='courses/', verbose_name='Gambar')),
                ('is_published', models.BooleanField(default=True, verbose_name='Dipublish')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('instructor', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='courses_taught', to='auth.user', verbose_name='Instruktur')),
            ],
            options={
                'verbose_name': 'Mata Kuliah',
                'verbose_name_plural': 'Mata Kuliah',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CourseContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Judul')),
                ('description', models.TextField(default='', verbose_name='Deskripsi')),
                ('video_url', models.CharField(blank=True, max_length=500, null=True, verbose_name='URL Video')),
                ('file_attachment', models.FileField(blank=True, null=True, upload_to='')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Urutan')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contents', to='courses.course', verbose_name='Kursus')),
            ],
            options={
                'verbose_name': 'Konten Kursus',
                'verbose_name_plural': 'Konten Kursus',
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='CourseMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('roles', models.CharField(choices=[('std', 'Siswa'), ('ast', 'Asisten')], default='std', max_length=3)),
                ('course_id', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='courses.course')),
                ('user_id', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='auth.user')),
            ],
            options={
                'verbose_name': 'Anggota Kelas',
                'verbose_name_plural': 'Anggota Kelas',
            },
        ),
        migrations.AddIndex(
            model_name='course',
            index=models.Index(fields=['price'], name='idx_course_price'),
        ),
        migrations.AddIndex(
            model_name='course',
            index=models.Index(fields=['instructor', 'price'], name='idx_course_instructor_price'),
        ),
        migrations.AddIndex(
            model_name='course',
            index=models.Index(fields=['is_published'], name='idx_course_published'),
        ),
    ]
