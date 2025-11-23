from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser
from .services import code_generate,send_code
from django.contrib.auth import login


class UserRegistrationsSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only = True,
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True)


    class Meta:
        model = CustomUser
        fields = (
            'username','email','password','password_confirm','first_name','last_name'
        )

    
    def validate(self,attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {"password":"Password fields didnt match."}
            )
        return attrs
    


    def create(self,validated_data):
        validated_data.pop("password_confirm")
        user = CustomUser.objects.create_user(**validated_data)
        return user
    


class UserLoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    class Meta:
        model = CustomUser
        fields = (
            'email','password'
        )

    def validate(self,attrs):
        email = attrs.get('email')
        password = attrs.get('password')


        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )
            if not user:
                raise serializers.ValidationError(
                    "User not found."
                )
            if not user.is_active:
                raise serializers.ValidationError(
                    "User is inactive."
                )
            
            attrs['user'] = user
            code=code_generate()
            request = self.context['request']
            request.session['2fa_user_id'] = user.id
            request.session['2fa_code'] = str(code)
            print(code)
            # send_code(email=email,code=code)
            return attrs
        else:
            raise serializers.ValidationError(
                'Must include "email" and "password".'
            )
        

class Verify2FASerializer(serializers.Serializer):



    code = serializers.CharField()
    

    def validate(self, data):
        request = self.context['request']
        session_code = request.session.get('2fa_code')
        user_id = request.session.get('2fa_user_id')

        if session_code is None or user_id is None:
            raise serializers.ValidationError("No active 2FA session")

        if data['code'] != session_code:
            raise serializers.ValidationError("Invalid verification code")

        return data

    def save(self):
        request = self.context['request']
        user = CustomUser.objects.get(id=request.session['2fa_user_id'])

        request.session.pop('2fa_code')
        request.session.pop('2fa_user_id')

        login(request, user)

        return {"detail": "Login successful"}
    


class UserResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email','password']