import logging
from datetime import date
from django.apps import apps

from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from mayan.apps.acls.models import AccessControlList
from mayan.apps.rest_api import generics
from rest_framework.views import APIView
from mayan.apps.document_states.tasks import task_launch_workflow_for

from ..models.document_models import Document
from ..models.document_type_models import DocumentType
from ..permissions import (
    permission_document_create, permission_document_properties_edit,
    permission_document_trash, permission_document_view
)
from ..serializers.document_serializers import (
    DocumentSerializer, DocumentChangeTypeSerializer,
    DocumentUploadSerializer
)

logger = logging.getLogger(name=__name__)


class APIDocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Returns the selected document details.
    delete: Move the selected document to the thrash.
    get: Return the details of the selected document.
    patch: Edit the properties of the selected document.
    put: Edit the properties of the selected document.
    """
    lookup_url_kwarg = 'document_id'
    mayan_object_permissions = {
        'GET': (permission_document_view,),
        'PUT': (permission_document_properties_edit,),
        'PATCH': (permission_document_properties_edit,),
        'DELETE': (permission_document_trash,)
    }
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

    def get_instance_extra_data(self):
        return {
            '_event_actor': self.request.user
        }


class APIDocumentListView(generics.ListCreateAPIView):
    """
    get: Returns a list of all the documents.
    post: Create a new document.
    """
    mayan_object_permissions = {
        'GET': (permission_document_view,),
    }
    ordering_fields = ('datetime_created', 'document_type', 'id', 'label')
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

    def perform_create(self, serializer):
        queryset = DocumentType.objects.all()

        queryset = AccessControlList.objects.restrict_queryset(
            permission=permission_document_create, queryset=queryset,
            user=self.request.user
        )

        serializer.validated_data['document_type'] = get_object_or_404(
            queryset=queryset, pk=serializer.validated_data['document_type_id']
        )
        super().perform_create(serializer=serializer)

    def get_instance_extra_data(self):
        return {
            '_event_actor': self.request.user
        }


class APIDocumentChangeTypeView(generics.GenericAPIView):
    """
    post: Change the type of the selected document.
    """
    lookup_url_kwarg = 'document_id'
    mayan_object_permissions = {
        'POST': (permission_document_properties_edit,),
    }
    queryset = Document.objects.all()
    serializer_class = DocumentChangeTypeSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document_type = DocumentType.objects.get(
            pk=request.data['document_type_id']
        )
        self.get_object().document_type_change(
            document_type=document_type, _user=self.request.user
        )
        
        if request.data['document_id']:
            task_launch_workflow_for(request.data['document_id'], request.data['workflow_id'])
        return Response(status=status.HTTP_200_OK)


class APIDocumentUploadView(generics.CreateAPIView):
    """
    post: Create a new document and a new document file.
    """
    serializer_class = DocumentUploadSerializer

    def perform_create(self, serializer):
        queryset = DocumentType.objects.all()

        queryset = AccessControlList.objects.restrict_queryset(
            permission=permission_document_create, queryset=queryset,
            user=self.request.user
        )

        serializer.validated_data['document_type'] = get_object_or_404(
            queryset=queryset, pk=serializer.validated_data['document_type_id']
        )
        super().perform_create(serializer=serializer)

    def get_instance_extra_data(self):
        return {
            '_event_actor': self.request.user
        }

class APISendMailReminders(APIView):

    def get(self, request, *args, **kwargs):

        pending_stages = Document.objects.raw(f"""SELECT nested.workflow as wx, nested.state_id as state_id, nested.state_id as id, count(nested.state_id) as ecount, nts.email
            FROM (
                SELECT DISTINCT ON(id) swi.id AS id, swi.workflow_id AS workflow, sws.id AS state_id, max(swil.datetime) AS datetime
                FROM document_states_workflowinstance swi, document_states_workflowinstancelogentry swil,
                document_states_workflowtransition swt, document_states_workflowstate sws
                WHERE swi.workflow_id in (SELECT * FROM public."nic_tracked_workflows")
                    AND swil.workflow_instance_id = swi.id
                    AND swil.transition_id = swt.id
                    AND swt.destination_state_id = sws.id
                group by swi.id, sws.id
                order by id, datetime desc
            ) AS nested, nic_tracked_states nts
            WHERE nested.state_id in (SELECT state_id FROM public."nic_tracked_states")
            AND nested.state_id = nts.state_id
            AND nested.datetime < (now() - '20 hours'::interval)
            group by nts.email, nested.state_id, nested.workflow

            UNION

            SELECT max(9) AS wx, max(66) AS state_id, max(swi.document_id) AS id, count(md.value) as ecount, md.value AS email
            FROM document_states_workflowinstance swi, document_states_workflowinstancelogentry swil, metadata_documentmetadata md
            WHERE swi.workflow_id = 9
            AND md.metadata_type_id = 16
            AND swil.transition_id = 308
            AND md.document_id = swi.document_id
            AND swil.workflow_instance_id = swi.id
            AND swi.document_id NOT IN (
            select wi.document_id
            FROM document_states_workflowinstance wi
            join document_states_workflowinstancelogentry wg
            on wg.workflow_instance_id = wi.id
            WHERE wi.workflow_id = 9
            AND wg.transition_id in (187, 302, 189, 307, 85, 87, 88, 89, 178))
            AND swil.datetime < (now() - '20 hours'::interval)
            group by md.value;"""
        )

        today = date.today()
        de = today.strftime("%d/%m/%Y")

        UserMailer = apps.get_model(
            app_label='mailer', model_name='UserMailer'
        )

        user_mailer = UserMailer.objects.get(pk=1)

        for stage in pending_stages:

            workflow = 'Edms'
            if stage.wx in [1, 6]:
                workflow = 'Claim'
            elif stage.wx == 13:
                workflow = 'Medical'
            elif stage.wx == 9:
                workflow = 'Leave'

            grammer = []
            if stage.ecount > 1:
                grammer.append("files have")
            else:
                grammer.append("file has")
    
            body = f"""
            Dear Sir/Madam,<br><br>

            This is a kind reminder, {stage.ecount} {workflow} {grammer[0]} not been attended to in a long time.<br><br>

            Below is a link to the state documents.<br>
            <a href='http://192.168.200.190/#/workflows/workflow_runtime_proxies/states/{stage.state_id}/documents/'>http://192.168.200.190/#/workflows/workflow_runtime_proxies/states/{stage.state_id}/documents/</a><br><br>

            ----<br>
            This email was sent by Mayan Edms.
            """

            user_mailer.send(body=body, subject=f'Delayed Edms files reminder. {de}', to=stage.email )

        return Response({"message":"done"}, status=status.HTTP_200_OK)
