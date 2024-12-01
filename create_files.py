import os
from faker import Faker


fake = Faker()


def create_fake_files(directory, num_files):
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Директорію '{directory}' створено.")

    for i in range(1, num_files + 1):
        file_name = f'file_{i}.txt'
        file_path = os.path.join(directory, file_name)

        # Генеруємо випадковий текст
        random_text = fake.text(max_nb_chars=200)  

        # Записуємо текст у файл
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(random_text)


if __name__ == "__main__":

    directory = './faker_files'
    create_fake_files(directory, num_files=10)
