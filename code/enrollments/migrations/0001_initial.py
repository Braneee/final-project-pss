from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Enrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enrolled_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True, verbose_name='Aktif')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrollments', to='auth.user', verbose_name='Siswa')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrollments', to='courses.course', verbose_name='Kursus')),
            ],
            options={
                'verbose_name': 'Pendaftaran',
                'verbose_name_plural': 'Pendaftaran',
                'ordering': ['-enrolled_at'],
                'unique_together': {('student', 'course')},
            },
        ),
        migrations.CreateModel(
            name='LessonProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_complete', models.BooleanField(default=False, verbose_name='Selesai')),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('enrollment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress', to='enrollments.enrollment', verbose_name='Pendaftaran')),
                ('content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress', to='courses.coursecontent', verbose_name='Konten')),
            ],
            options={
                'verbose_name': 'Progres Lesson',
                'verbose_name_plural': 'Progres Lesson',
                'unique_together': {('enrollment', 'content')},
            },
        ),
    ]
