import os
from django.core.files.storage import default_storage
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from gym_app.models import LegalDocument, IntranetProfile, User
from gym_app.serializers import LegalDocumentSerializer, IntranetProfileSerializer
from gym_app.utils.auth_utils import is_gym_staff
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from gym_app.views.layouts.sendEmail import send_template_email
from django.conf import settings

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_legal_intranet_documents(request):
    if not is_gym_staff(request.user):
        return Response(
            {'detail': 'No tienes permisos para acceder a la intranet.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Get all legal documents
    legal_intranet_documents = LegalDocument.objects.all()
    documents_serializer = LegalDocumentSerializer(
        legal_intranet_documents, 
        many=True, 
        context={'request': request}
    )
    
    # Get or create the intranet profile (should be only one instance)
    intranet_profile = IntranetProfile.objects.first()
    profile_data = None
    if intranet_profile:
        profile_serializer = IntranetProfileSerializer(
            intranet_profile,
            context={'request': request}
        )
        profile_data = profile_serializer.data
    
    # Count lawyers (users with role='lawyer' and is_gym_lawyer=True)
    lawyers_count = User.objects.filter(role='lawyer', is_gym_lawyer=True).count()
    
    # Count all users (excluding superusers/staff if needed, or count all)
    users_count = User.objects.filter(is_active=True).count()
    
    # Build response
    response_data = {
        'documents': documents_serializer.data,
        'profile': profile_data,
        'lawyers_count': lawyers_count,
        'users_count': users_count
    }
    
    return Response(response_data, status=status.HTTP_200_OK)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_report(request):
    """
    Handles the creation of a report request.

    This view processes form data and attached files from the request, 
    composes an email with the provided information, and sends it to 
    a predefined email address. All attached files are temporarily stored 
    to be included as email attachments and deleted after sending the email.

    Request body:
    - contract (string): Contract number.
    - initialDate (string): Start date of the report period.
    - endDate (string): End date of the report period.
    - paymentConcept (string): Concept of payment.
    - paymentAmount (string): Payment amount.
    - userName (string): User's first name.
    - userLastName (string): User's last name.
    - files (file[]): List of files attached as part of the request.

    Returns:
    - HTTP 201 Created: If the report is successfully sent via email.
    - HTTP 400 Bad Request: If there is an error processing the request.
    """
    if not is_gym_staff(request.user):
        return Response(
            {'detail': 'No tienes permisos para enviar cuentas de cobro.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        # Extract form data from the request
        contract = request.data.get("contract", "")
        initial_date = request.data.get("initialDate", "")
        end_date = request.data.get("endDate", "")
        payment_concept = request.data.get("paymentConcept", "")
        payment_amount = request.data.get("paymentAmount", "")
        
        # Extract user information
        user_name = request.data.get("userName", "")
        user_last_name = request.data.get("userLastName", "")
        full_name = f"{user_name} {user_last_name}".strip()

        # Retrieve attached files from the request.FILES object
        files = []
        for key in request.FILES:
            if key.startswith("files["):  # Match keys like "files[0]", "files[1]"
                files.append(request.FILES[key])

        # Temporarily save files to include them as email attachments
        attachments = []
        for file in files:
            file_path = default_storage.save(file.name, file)  # Save the file
            attachments.append({
                "path": os.path.join(settings.MEDIA_ROOT, file_path),  # Full path of the file
                "name": file.name,  # Original file name
            })

        # Prepare email subject and context for the "facturation" template
        email_subject = f"Cuenta de Cobro/Factura - {full_name}"
        recipient_email = "facturacion@gymconsultoresjuridicos.com"

        # Extract the user email provided by the requester (optional confirmation)
        user_email_raw = request.data.get("userEmail")
        if isinstance(user_email_raw, list):
            # If the value comes as a list (e.g., ['user@example.com']), grab the first element
            user_email = user_email_raw[0] if user_email_raw else None
        else:
            user_email = user_email_raw

        context = {
            "full_name": full_name,
            "contract": contract,
            "initial_date": initial_date,
            "end_date": end_date,
            "payment_concept": payment_concept,
            "payment_amount": payment_amount,
            "request_date": timezone.now().strftime("%Y-%m-%d %H:%M"),
        }

        # Send the main email using the helper utility
        send_template_email(
            template_name="facturation",
            subject=email_subject,
            to_emails=[recipient_email],
            context=context,
            attachments=[a["path"] for a in attachments],
        )

        # Send confirmation to the user if an email address was provided
        if user_email:
            send_template_email(
                template_name="facturation_receive_confirmation",
                subject=email_subject,
                to_emails=[user_email],
                context=context,
                attachments=[a["path"] for a in attachments],
            )

        # Clean up temporary files after the email is sent
        for attachment in attachments:
            os.remove(attachment["path"])

        # Return a success response
        return Response(
            {"message": "Informe creado y enviado con éxito."},
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        # Handle errors and return a bad request response
        return Response(
            {"error": f"Ha ocurrido un error al procesar la solicitud: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
