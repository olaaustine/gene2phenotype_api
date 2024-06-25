from rest_framework import serializers
import re

from ..models import (Disease, DiseaseOntologyTerm, DiseaseSynonym,
                      Attrib, LocusGenotypeDisease, OntologyTerm,
                      Source, GeneDisease)

from ..utils import (clean_string, get_ontology, get_ontology_source)


class DiseaseOntologyTermSerializer(serializers.ModelSerializer):
    """
        Serializer for the DiseaseOntologyTerm model.
        Links the disease to ontology terms imported from external ontology sources.
    """

    accession = serializers.CharField(source="ontology_term.accession")
    term = serializers.CharField(source="ontology_term.term")
    description = serializers.CharField(source="ontology_term.description", allow_null=True) # the description is optional
    source = serializers.CharField(source="ontology_term.source.name") # external source (ex: OMIM)

    class Meta:
        model = DiseaseOntologyTerm
        fields = ['accession', 'term', 'description', 'source']

class DiseaseSerializer(serializers.ModelSerializer):
    """
        Serializer for the Disease model.
        This serializer returns the ontology terms associated with the disease
        and synonyms names.
    """

    name = serializers.CharField()
    ontology_terms = serializers.SerializerMethodField()
    synonyms = serializers.SerializerMethodField()

    def get_ontology_terms(self, id):
        """
            Returns the ontology terms associated with the disease.
        """
        disease_ontologies = DiseaseOntologyTerm.objects.filter(disease=id)
        return DiseaseOntologyTermSerializer(disease_ontologies, many=True).data

    def get_synonyms(self, id):
        """
            Returns disease synonyms used in other sources.
        """
        synonyms = []
        disease_synonyms = DiseaseSynonym.objects.filter(disease=id)
        for d_synonym in disease_synonyms:
            synonyms.append(d_synonym.synonym)
        return synonyms

    class Meta:
        model = Disease
        fields = ['name', 'ontology_terms', 'synonyms']

class DiseaseDetailSerializer(DiseaseSerializer):
    """
        Serializer for the Disease model - extra fields.
    """
    last_updated = serializers.SerializerMethodField()

    def get_last_updated(self, id):
        """
            Returns the date an entry linked to the disease has been updated.
        """

        filtered_lgd_list = LocusGenotypeDisease.objects.filter(
            disease=id,
            is_reviewed=1,
            is_deleted=0,
            date_review__isnull=False
            ).latest('date_review'
                     ).date_review

        return filtered_lgd_list.date() if filtered_lgd_list else []

    def records_summary(self, id, user):
        """
            Returns a summary of the LGD records associated with the disease.
        """

        lgd_list = LocusGenotypeDisease.objects.filter(disease=id, is_deleted=0)

        if user.is_authenticated:
            lgd_select = lgd_list.select_related('disease', 'genotype', 'confidence'
                                               ).prefetch_related('lgd_panel', 'panel', 'lgd_variant_gencc_consequence', 'lgd_variant_type', 'lgd_molecular_mechanism', 'g2pstable_id'
                                                                  ).order_by('-date_review')

        else:
            lgd_select = lgd_list.select_related('disease', 'genotype', 'confidence'
                                               ).prefetch_related('lgd_panel', 'panel', 'lgd_variant_gencc_consequence', 'lgd_variant_type', 'lgd_molecular_mechanism', 'g2pstable_id'
                                                                  ).order_by('-date_review').filter(lgdpanel__panel__is_visible=1)


        lgd_objects_list = list(lgd_select.values('disease__name',
                                                  'lgdpanel__panel__name',
                                                  'stable_id__stable_id', # to get the stable_id stableID
                                                  'genotype__value',
                                                  'confidence__value',
                                                  'lgdvariantgenccconsequence__variant_consequence__term',
                                                  'lgdvarianttype__variant_type_ot__term',
                                                  'lgdmolecularmechanism__mechanism__value'))

        aggregated_data = {}
        for lgd_obj in lgd_objects_list:
            if lgd_obj['stable_id__stable_id'] not in aggregated_data.keys():
                variant_consequences = []
                variant_types = []
                molecular_mechanism = []
                panels = []

                panels.append(lgd_obj['lgdpanel__panel__name'])
                variant_consequences.append(lgd_obj['lgdvariantgenccconsequence__variant_consequence__term'])
                if lgd_obj['lgdvarianttype__variant_type_ot__term'] is not None:
                    variant_types.append(lgd_obj['lgdvarianttype__variant_type_ot__term'])
                if lgd_obj['lgdmolecularmechanism__mechanism__value'] is not None:
                    molecular_mechanism.append(lgd_obj['lgdmolecularmechanism__mechanism__value'])

                aggregated_data[lgd_obj['stable_id__stable_id']] = { 'disease':lgd_obj['disease__name'],
                                                          'genotype':lgd_obj['genotype__value'],
                                                          'confidence':lgd_obj['confidence__value'],
                                                          'panels':panels,
                                                          'variant_consequence':variant_consequences,
                                                          'variant_type':variant_types,
                                                          'molecular_mechanism':molecular_mechanism,
                                                          'stable_id':lgd_obj['stable_id__stable_id'] }

            else:
                if lgd_obj['lgdpanel__panel__name'] not in aggregated_data[lgd_obj['stable_id__stable_id']]['panels']:
                    aggregated_data[lgd_obj['stable_id__stable_id']]['panels'].append(lgd_obj['lgdpanel__panel__name'])
                if lgd_obj['lgdvariantgenccconsequence__variant_consequence__term'] not in aggregated_data[lgd_obj['stable_id__stable_id']]['variant_consequence']:
                    aggregated_data[lgd_obj['stable_id__stable_id']]['variant_consequence'].append(lgd_obj['lgdvariantgenccconsequence__variant_consequence__term'])
                if lgd_obj['lgdvarianttype__variant_type_ot__term'] not in aggregated_data[lgd_obj['stable_id__stable_id']]['variant_type'] and lgd_obj['lgdvarianttype__variant_type_ot__term'] is not None:
                    aggregated_data[lgd_obj['stable_id__stable_id']]['variant_type'].append(lgd_obj['lgdvarianttype__variant_type_ot__term'])
                if lgd_obj['lgdmolecularmechanism__mechanism__value'] not in aggregated_data[lgd_obj['stable_id__stable_id']]['molecular_mechanism'] and lgd_obj['lgdmolecularmechanism__mechanism__value'] is not None:
                    aggregated_data[lgd_obj['stable_id__stable_id']]['molecular_mechanism'].append(lgd_obj['lgdmolecularmechanism__mechanism__value'])

        return aggregated_data.values()

    class Meta:
        model = Disease
        fields = DiseaseSerializer.Meta.fields + ['last_updated']

class CreateDiseaseSerializer(serializers.ModelSerializer):
    """
        Serializer to add new disease.
    """
    ontology_terms = DiseaseOntologyTermSerializer(many=True, required=False)

    # Add synonyms

    def create(self, validated_data):
        """
            Add new disease and associated ontology terms (optional).
            To add a new disease first it checks if the disease name
            or the synonym name is already stored in G2P. If so, returns
            existing disease.
            If applicable, it associates the ontology terms to the disease.

            Args:
                validate_data: disease data to be inserted

            Returns:
                    disease object
        """

        disease_name = validated_data.get('name')
        ontologies_list = validated_data.get('ontology_terms')

        disease_obj = None

        # Clean disease name
        cleaned_input_disease_name = clean_string(str(disease_name))
        # Check if name already exists
        all_disease_names = Disease.objects.all()
        for disease_db in all_disease_names:
            cleaned_db_disease_name = clean_string(str(disease_db.name))
            if cleaned_db_disease_name == cleaned_input_disease_name:
                disease_obj = disease_db
        all_disease_synonyms = DiseaseSynonym.objects.all()
        for disease_synonym in all_disease_synonyms:
            cleaned_db_disease_syn = clean_string(str(disease_synonym.synonym))
            if cleaned_db_disease_syn == cleaned_input_disease_name:
                disease_obj = disease_synonym.disease

        if disease_obj is None:
            # TODO: give disease suggestions

            disease_obj = Disease.objects.create(
                name = disease_name
            )

        # Check if ontology is in db
        # The disease ontology is saved in the db as attrib type 'disease'
        for ontology in ontologies_list:
            ontology_accession = ontology['ontology_term']['accession']
            ontology_term = ontology['ontology_term']['term']
            ontology_desc = ontology['ontology_term']['description']
            disease_ontology_obj = None

            if ontology_accession is not None and ontology_term is not None:
                try:
                    ontology_obj = OntologyTerm.objects.get(accession=ontology_accession)

                except OntologyTerm.DoesNotExist:
                    # Check if ontology is from OMIM or Mondo
                    source = get_ontology_source(ontology_accession)

                    if source is None:
                        raise serializers.ValidationError({
                            "message": f"Invalid ID '{ontology_accession}' please input a valid ID from OMIM or Mondo"
                            })

                    elif source == "Mondo":
                        # Check if ontology accession is valid
                        mondo_disease = get_ontology(ontology_accession, source)
                        if mondo_disease is None:
                            raise serializers.ValidationError({"message": "Invalid Mondo ID",
                                                                   "Please check ID": ontology_accession})
                        elif mondo_disease == "query failed":
                            raise serializers.ValidationError({"message": f"Cannot query Mondo ID {ontology_accession}"})

                    # Replace '_' from mondo ID
                    ontology_accession = re.sub(r'\_', ':', ontology_accession)
                    ontology_term = re.sub(r'\_', ':', ontology_term)
                    # Insert ontology
                    if ontology_desc is None and len(mondo_disease['description']) > 0:
                        ontology_desc = mondo_disease['description'][0]

                    elif source == "OMIM":
                        omim_disease = get_ontology(ontology_accession, source)
                        # TODO: check if we can use the OMIM API in the future
                        if omim_disease == "query failed":
                            raise serializers.ValidationError({"message": f"Cannot query OMIM ID {ontology_accession}"})

                        if ontology_desc is None and omim_disease is not None and len(omim_disease['description']) > 0:
                            ontology_desc = omim_disease['description'][0]

                    source = Source.objects.get(name=source)
                    # Get attrib 'disease'
                    attrib_disease = Attrib.objects.get(
                        value = "disease",
                        type__code = "ontology_term_group"
                    )

                    ontology_obj = OntologyTerm.objects.create(
                                accession = ontology_accession,
                                term = ontology_term,
                                description = ontology_desc,
                                source = source,
                                group_type = attrib_disease
                    )

                attrib = Attrib.objects.get(
                    value="Data source",
                    type__code = "ontology_mapping"
                )

                try:
                    # Check if disease-ontology is stored in G2P
                    disease_ontology_obj = DiseaseOntologyTerm.objects.get(
                        disease = disease_obj,
                        ontology_term = ontology_obj,
                        mapped_by_attrib = attrib,
                    )
                except DiseaseOntologyTerm.DoesNotExist:
                    # Insert disease-ontology
                    disease_ontology_obj = DiseaseOntologyTerm.objects.create(
                        disease = disease_obj,
                        ontology_term = ontology_obj,
                        mapped_by_attrib = attrib,
                    )

        return disease_obj

    class Meta:
        model = Disease
        fields = ['name', 'ontology_terms']

class GeneDiseaseSerializer(serializers.ModelSerializer):
    """
        Serializer for the GeneDisease model.
        The GeneDisease model stores external gene-disease associations.
    """
    disease = serializers.CharField()
    identifier = serializers.CharField() # external identifier
    source = serializers.CharField(source="source.name")

    class Meta:
        model = GeneDisease
        fields = ['disease', 'identifier', 'source']
